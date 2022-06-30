import re
import os

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
            line = lines[i].decode('utf-8', errors='replace')
            if len(line) == 0:
                continue
            
            # bm time
            matcher = re.match(".*PASSED in (\d+) msec.*", line)
            if matcher:
                insert_data('execution_times', float(matcher.group(1)))
            
            # mmtk statistics
            if "MMTk Statistics Totals" in line:
                mmtk_keys = lines[i + 1].decode('utf-8').split()
                mmtk_values = lines[i + 2].decode('utf-8').split()
                assert len(mmtk_keys) == len(mmtk_values), "Error when reading MMTk statistics: num of keys does not match num of values"
                for j in range(0, len(mmtk_keys)):
                    insert_data(mmtk_keys[j], float(mmtk_values[j]))

        # initialie execution_times to empty in case all runs failed
        ret['execution_times'] = []
        for key in data:
            ret[key] = data[key]

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

# Given a log folder, return the result
def parse_run(log_folder, n_invocations = None):
    run_id = os.path.basename(os.path.normpath(log_folder))

    results = []
    logs = list_logs(log_folder)
    for l in logs:
        results.append(parse_log(os.path.join(log_folder, l), n_invocations))
    return run_id, results

# Given a run id, return the date
def parse_run_date(run_id):
    from datetime import datetime
    matcher = re.match(".*-(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})-(.*)-(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})", run_id)
    if matcher:
        return datetime(int(matcher['year']), int(matcher['month']), int(matcher['day']), int(matcher['hour']), int(matcher['minute']), int(matcher['second']))

# Given a yaml file path, return the file
def parse_yaml(path):
    import yaml
    with open(path, 'r') as file:
        content = file.read()
        return yaml.load(content, Loader=yaml.FullLoader)

# Given a parsed config (returned from parse_yaml) and a plan, return the config for the plan
def get_config_for_plan(config, plan):
    print(config)
    print(plan)
    for p in config['plans']:
        if p['plan'] == plan:
            return p
    return None

# Get the last log from baseline_root
def parse_baseline(result_repo_baseline_root):
    if not os.path.isdir(result_repo_baseline_root):
        return None, []

    # get baseline logs
    baseline_logs = list_logs(result_repo_baseline_root)
    if len(baseline_logs) == 0:
        return None, []
        
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