import re
import os

# Tail latency line for the timed (non-warmup) iteration, e.g.:
#   ===== DaCapo tail latency, metered 100ms smoothing: 50% 516 usec, 90% 14583 usec, 99% 23235 usec, 99.9% 35661 usec, 99.99% 60845 usec, max 84478 usec, measured over 200000 events =====
# Only request/response-style DaCapo Chopin benchmarks (cassandra, h2,
# lusearch, tomcat) run through probe.DacapoChopinCallback print this; other
# benchmarks simply never match, which is how we tell latency-capable
# benchmarks apart from the rest without hardcoding their names (see
# plot.plot_history's only_benchmarks_with_data param, used by
# history_report.py for the latency chart).
#
# We use "metered 100ms smoothing" rather than "simple" or "metered full
# smoothing": "simple" is raw per-request latency and doesn't correct for
# coordinated omission (a GC pause blocks the next request from even being
# issued, so it never shows up as a slow request); "metered full smoothing"
# spreads a single long pause's cost across the *entire* run, which produces
# huge, run-length-dependent percentiles that mostly reflect measurement
# smoothing rather than the shape of individual pauses. "metered 100ms
# smoothing" corrects for coordinated omission over a fixed short window, so
# the percentiles stay meaningful and comparable run over run.
LATENCY_METERED_100MS_RE = re.compile(
    r".*tail latency, metered 100ms smoothing: "
    r"50% ([\d.]+) usec, 90% ([\d.]+) usec, 99% ([\d.]+) usec, "
    r"99\.9% ([\d.]+) usec, 99\.99% ([\d.]+) usec, max ([\d.]+) usec")

LATENCY_KEYS = ['latency.p50', 'latency.p90', 'latency.p99', 'latency.p999', 'latency.p9999']

# MMTk stats print "n/a" for a counter that wasn't collected in that run
# (e.g. a plan-specific stat not applicable to the current plan). Treat it
# as 0 rather than failing to parse.
def parse_mmtk_value(s):
    if s == 'n/a':
        return 0.0
    return float(s)

# Given a log file and expected invocations, return the result
def parse_log(log_file, n_invocations = None):
    # return a dict of the parse result
    ret = {}

    ret['log_name'] = os.path.basename(log_file)

    # log_name is something like 'antlr.40000.2000.Trunk.ig.log.gz'
    file_name_matcher = re.match("(.*)\.\d+\.\d+\.([^\.]*)(\..*)?\.log\.gz", ret['log_name'])
    if file_name_matcher:
        ret['benchmark'] = file_name_matcher.group(1)
        ret['build'] = file_name_matcher.group(2)
    else:
        print("Unexpected log file name: %s" % ret['log_name'])
        return None

    # read execution time
    import gzip
    with gzip.open(log_file, 'r') as f:
        content = f.read()
        lines = content.splitlines()

        # key -> data array
        data = {}
        def insert_data(key, x):
            if key in data:
                data[key].append(x)
            else:
                data[key] = [x]

        for i in range(0, len(lines)):
            line = lines[i].decode('utf-8')
            if len(line) == 0:
                continue
            
            # bm time, as reported by the benchmark harness itself
            matcher = re.match(".*PASSED in (\d+) msec.*", line)
            if matcher:
                insert_data('execution_times', float(matcher.group(1)))

                # The tail latency block (if any) for this same invocation is
                # always 3 lines below PASSED: a "processed N requests" line,
                # then "simple", then "metered 100ms smoothing" (see
                # LATENCY_METERED_100MS_RE above).
                if i + 3 < len(lines):
                    latency_matcher = LATENCY_METERED_100MS_RE.match(lines[i + 3].decode('utf-8'))
                    if latency_matcher:
                        for key, value in zip(LATENCY_KEYS, latency_matcher.groups()):
                            insert_data(key, float(value))

            # mmtk statistics - only present when a probe-driving DaCapo
            # callback is configured (e.g. probe.DacapoChopinCallback).
            # Absent for JikesRVM, stock (non-MMTk) OpenJDK runs, or if no
            # callback is set at all - handled by the time.total fallback below.
            if "MMTk Statistics Totals" in line:
                mmtk_keys = lines[i + 1].decode('utf-8').split()
                mmtk_values = lines[i + 2].decode('utf-8').split()
                if len(mmtk_keys) == len(mmtk_values):
                    for j in range(0, len(mmtk_keys)):
                        insert_data(mmtk_keys[j], parse_mmtk_value(mmtk_values[j]))
                    # "Total time: X ms" - the MMTk-instrumented total
                    # (time.other + time.stw), measured from
                    # harness_begin/harness_end. More precise than
                    # execution_times since it excludes DaCapo harness
                    # overhead outside the timed region.
                    total_time_matcher = re.match(r"Total time: ([\d.]+) ms", lines[i + 3].decode('utf-8'))
                    if total_time_matcher:
                        insert_data('time.total', float(total_time_matcher.group(1)))
                else:
                    print(f"Unable to correctly parse values from {log_file}.")
                    print(f"* We have {len(mmtk_keys)} keys but {len(mmtk_values)} values.")
                    print(f"* This run will be ignored.")

        # initialie execution_times and time.total to empty in case all runs failed
        # (other code indexes ret['time.total'] directly, so the key must always exist)
        ret['execution_times'] = []
        ret['time.total'] = []
        # Likewise for latency: absent entirely for benchmarks that never print a
        # tail latency line, so callers can check `len(ret[key]) == 0` uniformly
        # instead of handling a missing key as a separate case.
        for key in LATENCY_KEYS:
            ret[key] = []
        for key in data:
            ret[key] = data[key]

        # time.total: prioritize the MMTk-instrumented "Total time" over the
        # benchmark's own reported time, but only if we got one properly
        # parsed per successful invocation - otherwise (no callback, so no
        # MMTk Statistics section at all; or a parse failure above) fall
        # back to execution_times entirely, rather than mixing sources.
        if len(ret['time.total']) != len(ret['execution_times']):
            ret['time.total'] = ret['execution_times']

    # if no n_invocations is passed in, we do not check how many results we have
    if n_invocations == None:
        return ret

    # otherwise check status
    n_results = len(ret['execution_times'])
    if n_results == 0:
        ret['status'] = 'fail'
    elif n_results == n_invocations:
        ret['status'] = 'success'
    elif n_results < n_invocations:
        ret['status'] = 'partial_fail'
    else:
        ret['status'] = 'unexpected_invocation_number'
    ret['succeeded_runs'] = n_results

    return ret

# Given a log folder (one run), return its commit info (e.g.
# {'mmtk-openjdk': '<sha>', 'mmtk-core': '<sha>'}), or None if there isn't
# one - e.g. older runs from before this was tracked, or plans like canary
# that run a fixed downloaded release rather than something built from a commit.
def parse_commit_info(log_folder):
    path = os.path.join(log_folder, 'commit-info.yml')
    if not os.path.isfile(path):
        return None
    return parse_yaml(path)

# Given a run's commit info (as returned by parse_commit_info, may be None),
# return a single display line for it (e.g. "mmtk-openjdk: abcdef0123,
# mmtk-core: 0123abcdef"), or None if there isn't one.
def format_commit_info_line(commit_info):
    if not commit_info:
        return None
    return ", ".join("%s: %s" % (k, v[:10]) for k, v in commit_info.items())

# Given a log folder, return the result
def parse_run(log_folder, n_invocations = None):
    run_id = os.path.basename(os.path.normpath(log_folder))

    results = []
    logs = list_logs(log_folder)
    for l in logs:
        results.append(parse_log(os.path.join(log_folder, l), n_invocations))

    commit_info = parse_commit_info(log_folder)

    return run_id, results, commit_info

# Given a run id, return the date
def parse_run_date(run_id):
    from datetime import datetime
    matcher = re.match(".*-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-(.*)-(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})", run_id)
    if matcher:
        return datetime(int(matcher['year']), int(matcher['month']), int(matcher['day']), int(matcher['hour']), int(matcher['minute']), int(matcher['second']))

# Given a note date, return the date object
def parse_note_date(note_date, note_time = None):
    from datetime import datetime
    date_matcher = re.match(r"(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})", note_date)
    if note_time is None:
        note_time = "0000"
    time_matcher = re.match(r"(?P<hour>\d{2})(?P<minute>\d{2})", note_time)
    if date_matcher and time_matcher:
        return datetime(int(date_matcher['year']), int(date_matcher['month']), int(date_matcher['day']), int(time_matcher['hour']), int(time_matcher['minute']))

# Given a yaml file path, return the file
def parse_yaml(path):
    import yaml
    with open(path, 'r') as file:
        content = file.read()
        return yaml.load(content, Loader=yaml.FullLoader)

# Given a parsed config (returned from parse_yaml) and a plan, return the config for the plan
def get_config_for_plan(config, plan):
    for p in config['plans']:
        if p['plan'] == plan:
            return p
    return None

# Get the last log from baseline_root
def parse_baseline(result_repo_baseline_root):
    if not os.path.isdir(result_repo_baseline_root):
        return None, [], None

    # get baseline logs
    baseline_logs = list_logs(result_repo_baseline_root)
    if len(baseline_logs) == 0:
        return None, [], None

    sort_logs(baseline_logs)
    latest_baseline_log = baseline_logs[-1]
    print("Latest baseline log: %s" % latest_baseline_log)

    # parse baseline
    baseline_results = parse_run(os.path.join(result_repo_baseline_root, latest_baseline_log))
    return baseline_results

def sort_logs(logs):
    # sort logs by date (in case we have logs from different machines)
    logs.sort(key = lambda x: parse_run_date(x))

def list_logs(path):
    files = os.listdir(path)
    filtered = list(filter(lambda f: f.endswith(".log.gz"), files))
    return filtered
