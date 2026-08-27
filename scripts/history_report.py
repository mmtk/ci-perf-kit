import os
from os import environ
import sys
import parse
import plot
import index_gen
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

import pprint
pp = pprint.PrettyPrinter(indent=2)


# Render every plan's history graph (full interactive HTML + sparkline PNG)
# for one runtime config into output_dir. Does NOT touch index.html - see
# index_gen.generate_index, which callers run separately (this lets a caller
# rendering multiple runtimes, e.g. render_all.py, regenerate the index once
# at the end instead of once per runtime).
def render_plans(config_path, result_repo_vm_root, result_repo_baseline_root, output_dir, only_plan=None):
    config = parse.parse_yaml(config_path)
    print(config)

    prefix = config['name']

    if only_plan is not None:
        plan_path = os.path.join(result_repo_vm_root, only_plan)
        if not os.path.isdir(plan_path):
            print("No results found yet for plan '%s' at %s" % (only_plan, plan_path))
            return
        plans = [only_plan]
    else:
        # all subfolders are plan names, or "canary" for the canary version
        plans = os.listdir(result_repo_vm_root)

    # check from date and to date
    from_date_env = environ.get("FROM_DATE")
    to_date_env = environ.get("TO_DATE")
    if from_date_env is not None:
        from_date = datetime.datetime.strptime(from_date_env, "%Y-%m-%d").date()
    else:
        # default start date
        from_date = datetime.date(2020, 6, 1)

    if to_date_env is not None:
        to_date = datetime.datetime.strptime(to_date_env, "%Y-%m-%d").date()
    else:
        to_date = date.today() + datetime.timedelta(days=1) # one day after today (so the last day is today)

    baseline_run_id, baseline_results, _ = parse.parse_baseline(result_repo_baseline_root)
    # pp.pprint(baseline_results)

    excluded_runs = plot.get_excluded_runs_from_env_var('HISTORY_EXCLUDE_RUNS')

    for plan in plans:
        # The path for all logs for the plan, such as /home/yilin/Code/ci-perf-kit/result_repo/openjdk/immix
        plan_path = os.path.join(result_repo_vm_root, plan)
        # Get all the runs for the plan, such as ['rat-2021-08-24-Tue-163625']
        logs = [x for x in os.listdir(plan_path) if os.path.isdir(os.path.join(plan_path, x))]

        if (len(logs)) == 0:
            continue

        # Sort logs and find the last log. Plot for the benchmarks used in the last log.
        parse.sort_logs(logs)
        runs = {}
        run_commit_info = {}
        last_run = None
        for l in logs:
            run_id, results, commit_info = parse.parse_run(os.path.join(result_repo_vm_root, plan, l))
            if run_id not in excluded_runs:
                runs[run_id] = results
                run_commit_info[run_id] = commit_info
                last_run = run_id

        # figure out what benchmarks we should plot in the graph. We use the benchmarks that appeared in the last run
        benchmarks = [r['benchmark'] for r in runs[last_run]]

        print("Plan: %s" % plan)
        print("Last run: %s" % last_run)
        print("Benchmarks: %s" % benchmarks)
        # print(logs)

        # figure out the baseline and get the result for the baseline
        plan_config = parse.get_config_for_plan(config, plan)
        assert plan_config != None, "Cannot get config for plan"
        build_info = prefix

        # Plans opted into `time: true` (see configs/openjdk-plot.yml,
        # configs/jikesrvm-plot.yml) get a total/mutator/STW time history page -
        # the full interactive page, plus a compact "sparkline" PNG of the same
        # data for index.html's dashboard thumbnail (see plot.py's `sparkline`
        # param and index_gen.py's card generation, both of which key off the
        # "_time_history" name below).
        if plan_config.get('time', False):
            baseline_builds = plan_config['baseline']
            print("Baseline: %s" % baseline_builds)

            # time.total prioritizes the MMTk-instrumented "Total time" (time.other +
            # time.stw) when a probe-driving callback is configured, falling back to
            # the benchmark's own reported execution_times otherwise (see parse.py).
            baseline = plot.calculate_baseline(baseline_results, baseline_builds, "time.total")
            pp.pprint(baseline)

            fig = plot.plot_history(build_info, runs, plan, benchmarks, from_date, to_date, "time.total", baseline, config['notes'].copy(), run_commit_info)
            path = os.path.join(output_dir, "%s_%s_time_history.html" % (prefix, plan))
            fig.write_html(path, include_plotlyjs='cdn')

            sparkline_fig = plot.plot_history(build_info, runs, plan, benchmarks, from_date, to_date, "time.total", baseline, config['notes'].copy(), run_commit_info, sparkline=True)
            png_path = os.path.join(output_dir, "%s_%s_time_history.png" % (prefix, plan))
            # scale=2 for a crisp thumbnail on high-DPI displays; index.html displays it at
            # plot.SPARKLINE_GRAPH_WIDTH logical CSS pixels regardless of this scale factor.
            sparkline_fig.write_image(png_path, scale=2)

        # Every plan gets all three percentile-based history charts, regardless of
        # what configs/*-plot.yml says for it - the exact same chart as the time
        # history above (plot.plot_history), just with a <metric>.p9999 primary
        # series (instead of time.total - p99.99 is the tail percentile people
        # actually watch for regressions) and a secondary_metrics overlay of the
        # less extreme percentile(s), on a log-scale Y axis (log_y) since tail
        # percentiles span two-plus orders of magnitude versus the rest. The
        # `latency`/`time_to_yield`/`pause_time` config flags no longer gate
        # whether a chart is rendered - only whether index_gen.py's dashboard shows
        # its card by default (see index_gen._collect_cards) - so a plan without
        # the flag still gets a real page, just tucked into the dashboard's
        # collapsed "more metrics" section unless a viewer opts in.
        # There's no percentile equivalent of the stock-JDK `baseline` dict, and only
        # benchmarks with data anywhere in their history get a row
        # (only_benchmarks_with_data) - not every benchmark reports every metric (e.g.
        # tail latency is only reported by request/response-style DaCapo benchmarks
        # like cassandra, h2, lusearch, tomcat). Named "_<file_suffix>_history.{html,png}"
        # so index_gen.py can reference each distinctly from the "_time_history" pair
        # above and from each other.
        def render_percentile_history(metric_key, secondary_metrics, title_suffix, data_label, unit, file_suffix):
            fig = plot.plot_history(build_info, runs, plan, benchmarks, from_date, to_date, "%s.p9999" % metric_key, None, config['notes'].copy(), run_commit_info,
                                     secondary_metrics=secondary_metrics, title_suffix=title_suffix,
                                     primary_label="p99.99", secondary_clamp=False, only_benchmarks_with_data=True,
                                     data_label=data_label, unit=unit, secondary_show_percentage=False, log_y=True)
            if fig is None:
                print("Plan %s has no benchmark with %s data yet." % (plan, metric_key))
                return

            path = os.path.join(output_dir, "%s_%s_%s_history.html" % (prefix, plan, file_suffix))
            fig.write_html(path, include_plotlyjs='cdn')

            sparkline_fig = plot.plot_history(build_info, runs, plan, benchmarks, from_date, to_date, "%s.p9999" % metric_key, None, config['notes'].copy(), run_commit_info,
                                               secondary_metrics=secondary_metrics,
                                               primary_label="p99.99", secondary_clamp=False, only_benchmarks_with_data=True, sparkline=True,
                                               data_label=data_label, unit=unit, secondary_show_percentage=False, log_y=True)
            png_path = os.path.join(output_dir, "%s_%s_%s_history.png" % (prefix, plan, file_suffix))
            sparkline_fig.write_image(png_path, scale=2)

        render_percentile_history("latency", plot.LATENCY_SECONDARY_METRICS,
                                   "(Tail latency)", "p99.99 latency", "usec", "latency")
        render_percentile_history("time-to-yield", plot.TIME_TO_YIELD_SECONDARY_METRICS,
                                   "(Time-to-yield)", "p99.99 time-to-yield", "ms", "time_to_yield")
        render_percentile_history("pause-time", plot.PAUSE_TIME_SECONDARY_METRICS,
                                   "(Pause time)", "p99.99 pause time", "ms", "pause_time")


if __name__ == "__main__":
    if len(sys.argv) not in (5, 6):
        print("Usage: python history_report.py <config> <result_repo_vm_root> <result_repo_baseline_root> <output_dir> [plan_name]")
        sys.exit(1)

    config_path = sys.argv[1]
    result_repo_vm_root = sys.argv[2]
    result_repo_baseline_root = sys.argv[3]
    output_dir = sys.argv[4]
    # Optional: only (re)generate this one plan's graph, instead of every plan
    # folder present in the result repo. Callers that just ran a single plan
    # (see openjdk-report.sh) pass this so the report step is scoped to - and
    # only commits/deploys - that plan's own updated graph, rather than
    # reprocessing (and re-publishing) all of them on every run.
    only_plan = sys.argv[5] if len(sys.argv) == 6 else None

    render_plans(config_path, result_repo_vm_root, result_repo_baseline_root, output_dir, only_plan)

    # Regenerate index.html into output_dir alongside whatever this run just wrote.
    # Reads from *every* runtime's default config (see
    # index_gen.DEFAULT_CONFIG_FILENAMES), not just this run's own `config` - so
    # even a single-plan run (only_plan set) leaves a complete, correct index
    # behind, not one that only lists the plan it touched.
    index_gen.generate_index(output_dir)
