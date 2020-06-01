import os
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

log_folder_root = "running/results/log"

runs = {}
log_folders = os.listdir(log_folder_root)
log_folders.sort()
for log_folder in log_folders:
    run_id, results = parse.parse_run(os.path.join(log_folder_root, log_folder))
    runs[run_id] = results

# plans = ['NoGC', 'SemiSpace']
benchmarks = ['antlr', 'fop']

from_date = datetime.date(2020, 5, 10)
to_date = date.today()
fig = plot.plot_history(runs, "NoGC_Branch", benchmarks, from_date, to_date)

fig.write_html("history.html")