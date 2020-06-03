import plotly
from plotly.subplots import make_subplots
from datetime import timedelta, date
import parse

# runs: all the runs for a certain build (as a dictionary from run_id -> run results)
# plan: the plan to plot
# benchmarks: benchmarks to plot
# start_date, end_date: plot data between the given date range
def plot_history(runs, plan, benchmarks, start_date, end_date):
    # make subplots
    fig = make_subplots(
        rows = len(benchmarks)
    )

    row = 1
    for bm in benchmarks:
        # extract results
        print(plan + ' ' + bm)

        y = history_per_day(runs, plan, bm, start_date, end_date)
        y = normalize_history(y)
        x = list(range(0, len(y)))
        fig.add_trace(plotly.graph_objects.Scatter(x = x, y = y), row = row, col = 1)
        row += 1
    
    return fig


def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


# Returns one array, each element is the average execution time for the benchmark on one day, the index represents the days from the start date
def history_per_day(runs, plan, benchmark, start_date, end_date):
    # ordered runs
    run_ids = list(runs.keys())
    run_ids.sort()

    ret = []

    # record last run. If we dont have a run for that day, we use last run
    last_run = None
    # iterate through all the days in the given range
    for single_date in daterange(start_date, end_date):
        date_str = single_date.strftime("%Y-%m-%d")
        # find the last run_id before single_date
        runs_of_the_day = [x for x in run_ids if date_str in x]
        if len(runs_of_the_day) != 0:
            last_run = runs_of_the_day[-1]
        
        execution_time = 0
        if last_run is not None:
            execution_time = average_time(runs[last_run], plan, benchmark)

        print("Run for %s: %s (%s)" % (single_date, last_run, execution_time))
        ret.append(execution_time)
    
    return ret


# Use first non-zero value as 100%, normalize each value
def normalize_history(arr):
    if (len(arr)) == 0:
        return arr

    ret = []
    first_non_zero = None
    for x in arr:
        if x != 0 and first_non_zero is None:
            first_non_zero = x
        
        if first_non_zero is None:
            ret.append(1)
        else:
            ret.append(x / first_non_zero)
    
    return ret


def average_time(run, plan, benchmark):
    for bm_run in run:
        if bm_run['benchmark'] == benchmark and bm_run['build'].lower() == plan.lower():
            if len(bm_run['execution_times']) != 0:
                return sum(bm_run['execution_times']) / len(bm_run['execution_times'])
            else:
                return None