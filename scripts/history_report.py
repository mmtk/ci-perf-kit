import os
import parse

import plotly
from plotly.subplots import make_subplots

log_folder_root = "running/results/log"

runs = {}
log_folders = os.listdir(log_folder_root)
log_folders.sort()
for log_folder in log_folders:
    run_id, results = parse.parse_run(os.path.join(log_folder_root, log_folder))
    runs[run_id] = results

plans = ['NoGC', 'SemiSpace']
benchmarks = ['antlr', 'fop']

# make subplots
fig = make_subplots(
    rows = len(plans) * len(benchmarks)
)

row = 1
for gc in plans:
    for bm in benchmarks:
        # extract results
        print(gc + ' ' + bm)
        y = []
        for run in runs.keys():
            for bm_run in runs[run]:
                if bm_run['benchmark'] == bm and bm_run['build'] == gc + "_Branch":
                    print(bm_run)
                    if len(bm_run['execution_times']) != 0:
                        print("%f / %f" % (sum(bm_run['execution_times']), len(bm_run['execution_times'])))
                        y.append(sum(bm_run['execution_times']) / len(bm_run['execution_times']))
                    else:
                        y.append(0)

        print(runs.keys())
        print(y)
        fig.add_trace(plotly.graph_objects.Scatter(x = list(runs.keys()), y = y), row = row, col = 1)
        row += 1

fig.write_html("history.html")