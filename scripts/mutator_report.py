import os
from os import environ
import sys
import parse
import plot
import datetime
from datetime import date

import plotly
from plotly.subplots import make_subplots

if len(sys.argv) != 3:
    print("Usage: python mutator_report.py <result_repo_mutator_root> <output_dir>")

result_repo_mutator_root = sys.argv[1]
output_dir = sys.argv[2]

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

logs = [x for x in os.listdir(result_repo_mutator_root) if os.path.isdir(os.path.join(result_repo_mutator_root, x))]

if (len(logs)) == 0:
    print("No logs found")
    sys.exit(1)

runs = {}
last_run = None
for l in logs:
    run_id, results = parse.parse_run(os.path.join(result_repo_mutator_root, l))
    runs[run_id] = results
    last_run = run_id

# figure out what benchmarks we should plot in the graph. We use the benchmarks that appeared in the last run
benchmarks = list(set([r['benchmark'] for r in runs[last_run]]))
plans = list(set([r['build'] for r in runs[last_run]]))
print(last_run)
print(benchmarks)
print(plans)

fig = plot.plot_multi_plans_history(runs, plans, benchmarks, from_date, to_date, "time.other")
path = os.path.join(output_dir, "mutator_history.html")
fig.write_html(path)
