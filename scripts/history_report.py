import os
from os import environ
import sys
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

if len(sys.argv) != 4:
    print("Usage: python history_report.py <result_repo_vm_root> <output_dir> <prefix>")

result_repo_vm_root = sys.argv[1]
output_dir = sys.argv[2]
prefix = sys.argv[3]

# all subfolders are plan names
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

for plan in plans:
    logs = [x for x in os.listdir(os.path.join(result_repo_vm_root, plan)) if os.path.isdir(os.path.join(result_repo_vm_root, plan, x))]

    if (len(logs)) == 0:
        continue
    
    runs = {}
    logs.sort()
    last_run = None
    for l in logs:
        run_id, results = parse.parse_run(os.path.join(result_repo_vm_root, plan, l))
        runs[run_id] = results
        last_run = run_id
    
    # figure out what benchmarks we should plot in the graph. We use the benchmarks that appeared in the last run
    benchmarks = [r['benchmark'] for r in runs[last_run]]

    print(plan)
    print(last_run)
    print(benchmarks)
    
    # plot
    fig = plot.plot_history(runs, plan, benchmarks, from_date, to_date, "execution_times")
    path = os.path.join(output_dir, "%s_%s_history.html" % (prefix, plan))
    fig.write_html(path)
