import os
import sys
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

if len(sys.argv) != 2:
    print("Usage: python history_report.py <result_repo_vm_root>")

result_repo_vm_root = sys.argv[1]

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
    fig.write_html("%s_history.html" % plan)

# runs = {}
# log_folders = os.listdir(log_folder_root)
# log_folders.sort()
# for log_folder in log_folders:
#     run_id, results = parse.parse_run(os.path.join(log_folder_root, log_folder))
#     runs[run_id] = results

# # plans = ['NoGC', 'SemiSpace']
# benchmarks = ['antlr', 'fop']

# from_date = datetime.date(2020, 6, 1)
# to_date = date.today() + datetime.timedelta(days=1)

# fig1 = plot.plot_history(runs, "NoGC", benchmarks, from_date, to_date)
# fig1.write_html("nogc_history.html")

# fig2 = plot.plot_history(runs, "SemiSpace", benchmarks, from_date, to_date)
# fig2.write_html("semispace_history.html")