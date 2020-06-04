import os
import sys
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

if len(sys.argv) != 3:
    print("Usage: python history_report.py <result_repo_vm_root> <output_dir>")

result_repo_vm_root = sys.argv[1]
output_dir = sys.argv[2]

# all subfolders are plan names
plans = os.listdir(result_repo_vm_root)

from_date = datetime.date(2020, 6, 1)
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
    fig = plot.plot_history(runs, plan, benchmarks, from_date, to_date)
    path = os.path.join(output_dir, "%s_history.html" % plan)
    fig.write_html(path)
