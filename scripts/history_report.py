import os
from os import environ
import sys
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

import pprint
pp = pprint.PrettyPrinter(indent=2)

if len(sys.argv) != 5:
    print("Usage: python history_report.py <config> <result_repo_vm_root> <result_repo_baseline_root> <output_dir>")
    sys.exit(1)

config_path = sys.argv[1]
result_repo_vm_root = sys.argv[2]
result_repo_baseline_root = sys.argv[3]
output_dir = sys.argv[4]

config = parse.parse_yaml(config_path)
print(config)

prefix = config['name']

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

baseline_run_id, baseline_results = parse.parse_baseline(result_repo_baseline_root)
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
    last_run = None
    for l in logs:
        run_id, results = parse.parse_run(os.path.join(result_repo_vm_root, plan, l))
        if run_id not in excluded_runs:
            runs[run_id] = results
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
    baseline_builds = plan_config['baseline']
    print("Baseline: %s" % baseline_builds)

    baseline = plot.calculate_baseline(baseline_results, baseline_builds, "execution_times")
    pp.pprint(baseline)

    build_info = prefix

    # plot
    fig = plot.plot_history(build_info, runs, plan, benchmarks, from_date, to_date, "execution_times", baseline, config['notes'].copy())
    path = os.path.join(output_dir, "%s_%s_history.html" % (prefix, plan))
    fig.write_html(path)
