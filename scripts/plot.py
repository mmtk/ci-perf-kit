import plotly
from plotly.graph_objs import *
from datetime import timedelta, date
import parse
import numpy as np
import math

# runs: all the runs for a certain build (as a dictionary from run_id -> run results)
# plan: the plan to plot
# benchmarks: benchmarks to plot
# start_date, end_date: plot data between the given date range
def plot_history(runs, plan, benchmarks, start_date, end_date, data_key):
    layout = {
        "title": plan,
        # "margin": {"t": 80},
        # "width": 500,
        # "height": 500
    }
    
    n_benchmarks = len(benchmarks)
    row = 1
    
    traces = []
    annotations = []

    # we want all the traces use the same Y range so it is easier to interpret the plot. These two variables record the upper and lower of Y range
    y_range_upper = - float("inf")
    y_range_lower = float("inf")

    for bm in benchmarks:
        # extract results
        print(plan + ' ' + bm)

        # y, std = history_per_day(runs, plan, bm, start_date, end_date, data_key)
        y, std = history_per_run(runs, plan, bm, data_key)
        x = list(range(0, len(y)))
        x_labels = list(runs.keys())
        x_labels.sort()

        # From now, all y's are normalized to this baseline
        nonzero_y = [i for i in y[:-1] if i != 0] # we dont want 0 as baseline, and we should not use the most recent data as baseline
        y_baseline = min(nonzero_y)
        y_max = max(y) / y_baseline
        y_min = min(nonzero_y) / y_baseline

        # update range
        if y_max > y_range_upper:
            y_range_upper = y_max
        if y_min < y_range_lower:
            y_range_lower = y_min

        # normalize y
        y = normalize_to(y, y_baseline)
        std = normalize_to(std, y_baseline)

        x_axis = "x%d" % row
        y_axis = "y%d" % row

        # history
        history_trace = {
            "name": bm,
            "hoverinfo": "text",
            "line": {"width": 1},
            "type": "scatter",
            "x": x,
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
        }
        traces.append({**history_trace, **{
            "line": {"width": 3, "color": "black"},
            "y": y,
            "text": ["history: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
        }})
        layout["xaxis%d" % row] = {
            "ticks": "",
            "anchor": x_axis,
            "domain": [0, 1],
            "mirror": False,
            "showgrid": False,
            "showline": False,
            "zeroline": False,
            "showticklabels": False,
        }
        # e.g. if we have 4 rows (row = 5 at the moment)
        # the y domain for each trace should be [0, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1]
        ydomain = [1 - 1/n_benchmarks * row, 1 - 1/n_benchmarks * (row - 1)]
        layout["yaxis%d" % row] = {
            "title": bm,
            "ticks": "",
            "anchor": y_axis,
            "domain": ydomain,
            "mirror": False,
            "showgrid": False,
            "showline": True,
            "zeroline": False,
            "showticklabels": False,
            # "range": [y_min * 0.9, y_max * 1.1],
            "autorange": False,
        }

        # highlight max/min
        def keep_first(arr, f):
            ret = []
            first = True
            for x in arr:
                if f(x) and first:
                    ret.append(x)
                    first = False
                else:
                    ret.append(None)
            return ret
        def keep_last(arr, f):
            r = arr.copy()
            r.reverse()
            res = keep_first(r, f)
            res.reverse()
            return res

        y_max_array = keep_first(y, lambda x: x == y_max) # keep max, leave others as None
        traces.append({**history_trace, **{
            "mode": "markers",
            "y": y_max_array,
            "text": ["history max: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
            "marker": { "size": 15, "color": "red" },
            "showlegend": False,
        }})
        y_min_array = keep_first(y, lambda x: x == y_min) # keep min, leave others as None
        traces.append({**history_trace, **{
            "mode": "markers",
            "y": y_min_array,
            "text": ["history min: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
            "marker": { "size": 15, "color": "green" },
            "showlegend": False,
        }})
        # labeling max/min
        max_i = y.index(y_max)
        annotation = {
            "xref": x_axis,
            "yref": y_axis,
        }
        annotations.append({**annotation, **{
            "x": x[max_i],
            "y": y_max,
            "text": "%s: %.2f" % (x_labels[max_i], y_max),
            "font": {"color": "red"}
        }})
        min_i = y.index(y_min)
        annotations.append({**annotation, **{
            "x": x[min_i],
            "y": y_min,
            "text": "%s: %.2f" % (x_labels[min_i], y_min),
            "font": {"color": "green"}
        }})

        # highlight current
        current = y[-1]
        current_std = std[-1]
        # determine if current is improvement or degradation
        if current + current_std < y_min:
            # improvement
            current_color = "green"
        elif current - current_std > y_min:
            # degradation
            current_color = "red"
        else:
            # none of the above
            current_color = "black"

        y_last_array = keep_last(y, lambda x: x == current)
        traces.append({**history_trace, **{
            "mode": "markers",
            "y": y_last_array,
            "text": ["history current: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
            "marker": {"size": 15, "color": "black"},
            "showlegend": False,
        }})
        annotations.append({**annotation, **{
            "x": x[-1],
            "y": y[-1],
            "text": "%.2f" % current,
            "font": {"color": current_color, "size": 60},
            "ax": 100,
        }})

        # moving average
        y_moving_average = moving_average(y, 10)
        traces.append({
            "name": bm,
            "hoverinfo": "text",
            # "fill": "tozeroy",
            # "mode": "lines",
            "line": {"width": 1, "color": "gray"},
            "type": "scatter",
            "x": x,
            "y": y_moving_average,
            "text": ["10-p moving avg: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y_moving_average)],
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
        })

        # variance (+-std dev from moving average)
        variance_trace = {
            "name": bm,
            "hoverinfo": "text",
            "mode": "lines",
            "line_color": "gray",
            "line": {"width": 0},
            "x": x,
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
        }
        variance_up = list(map(lambda a, b: a + b, y_moving_average, std))
        traces.append({**variance_trace, **{
            "y": variance_up,
            "text": ["moving avg + std dev: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, variance_up)],
        }})
        variance_down = list(map(lambda a, b: a - b, y_moving_average, std))
        traces.append({**variance_trace, **{
            "fill": "tonexty",
            "y": variance_down,
            "text": ["moving avg - std dev: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, variance_down)],
        }})

        row += 1

    # fix range for all the traces
    y_range = [y_range_lower - 0.02, y_range_upper + 0.02]
    for i in range(1, row):
        layout["yaxis%d" % i]["range"] = y_range

    fig = Figure(data = Data(traces), layout = layout)
    for anno in annotations:
        fig.add_annotation(anno)
    return fig


def plot_multi_plans_history(runs, plans, benchmarks, start_date, end_date, data_key):
    # whether we should show legend - only show legend for a plan when it is the first time we add a trace for this plan
    show_legend = {}
    for p in plans:
        show_legend[p] = True

    row = 1
    traces = []
    for bm in benchmarks:
        print(bm)

        for p in plans:
            print(p)
            # y, std = history_per_day(runs, p, bm, start_date, end_date, data_key)
            # y = normalize_history(y)
            y, std = history_per_run(runs, p, bm, data_key)
            x = list(range(0, len(y)))
            x_labels = list(runs.keys())
            x_labels.sort()

            trace = {
                "name": p,
                "legendgroup": p,
                "showlegend": show_legend[p],
                "hoverinfo": "text",
                "mode": "lines",
                "line": {"width": 1},
                "type": "scatter",
                "x": x,
                "y": y,
                "text": ["%s: %s, %.2f" % (x, p, y) for (x, y) in zip(x_labels, y)],
                "xaxis": "x%d" % row,
                "yaxis": "y%d" % row
            }
            # dont show legend for this plan any more
            show_legend[p] = False

            traces.append(trace)
        
        row += 1

        data = Data(traces)
    
    layout = {
        "title": data_key,
        "margin": {"t": 80},
        # "width": 500,
        # "height": 500
    }
    for i in range(1, row):
        layout["xaxis%d" % i] = {
            "ticks": "",
            "anchor": "y%d" % i,
            "domain": [0, 1],
            "mirror": False,
            "showgrid": False,
            "showline": False,
            "zeroline": False,
            "showticklabels": False,
        }
        # e.g. if we have 4 rows (row = 5 at the moment)
        # the y domain for each trace should be [0, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1]
        ydomain = [1 - 1/(row - 1) * i, 1 - 1/(row - 1) * (i - 1)]
        layout["yaxis%d" % i] = {
            "title": benchmarks[i - 1],
            "ticks": "",
            "anchor": "x%d" % i,
            "domain": ydomain,
            "mirror": False,
            "showgrid": False,
            "showline": False,
            "zeroline": False,
            "showticklabels": False,
            "autorange": True,
        }
    
    fig = Figure(data = data, layout = layout)
    return fig


def daterange(start_date, end_date):
    for n in range(int ((end_date - start_date).days)):
        yield start_date + timedelta(n)


def moving_average(array_numbers, p):
    window_sum = 0
    window_len = 0

    n = len(array_numbers)
    ma = []
    for i in range(0, n):
        if window_len < p:
            window_sum += array_numbers[i]
            window_len += 1
        else:
            window_sum -= array_numbers[i - p]
            window_sum += array_numbers[i]
        
        ma.append(window_sum / float(window_len))
    
    assert len(array_numbers) == len(ma)
    return ma


# Returns two arrays:
# The first array is average execution time for the benchmark on one day.
# The second array represents standard deviation.
def history_per_day(runs, plan, benchmark, start_date, end_date, data_key):
    # ordered runs
    run_ids = list(runs.keys())
    run_ids.sort()

    avg = []
    std = []

    # record last run. If we dont have a run for that day, we use last run
    last_run = None
    # iterate through all the days in the given range
    for single_date in daterange(start_date, end_date):
        date_str = single_date.strftime("%Y-%m-%d")
        # find the last run_id before single_date
        runs_of_the_day = [x for x in run_ids if date_str in x]
        if len(runs_of_the_day) != 0:
            last_run = runs_of_the_day[-1]
        
        result = 0, 0
        if last_run is not None:
            result = average_time(runs[last_run], plan, benchmark, data_key)
            if result is None:
                result = 0, 0

        print("Run for %s: %s (%s +- %s)" % (single_date, last_run, result[0], result[1]))
        avg.append(result[0])
        std.append(result[1])
    
    return avg, std


def history_per_run(runs, plan, benchmark, data_key):
    # ordered runs
    run_ids = list(runs.keys())
    run_ids.sort()

    avg = []
    std = []

    for rid in run_ids:
        result = average_time(runs[rid], plan, benchmark, data_key)
        if result is None:
            result = 0, 0
        
        print("Run for %s: %s +/- %s" % (rid, result[0], result[1]))
        avg.append(result[0])
        std.append(result[1])

    return avg, std


# Use first non-zero value as 0, normalize each value to be a percentage compared to the first non-zero value
def normalize_history(arr):
    if (len(arr)) == 0:
        return arr

    print(arr)
    ret = []
    first_non_zero = None
    for x in arr:
        if x != 0 and first_non_zero is None:
            first_non_zero = x
        
        if first_non_zero is None:
            ret.append(0)
        else:
            ret.append((x - first_non_zero) / first_non_zero)
    
    return ret


def normalize_to(arr, base):
    assert base != 0, "Cannot normalize to a zero value"
    return list(map(lambda x: x / base, arr))


def average_time(run, plan, benchmark, data_key):
    for bm_run in run:
        if bm_run['benchmark'] == benchmark and (bm_run['build'].lower() == plan.lower() or bm_run['build'].lower().endswith(plan.lower())):
            if data_key in bm_run and len(bm_run[data_key]) != 0:
                return sum(bm_run[data_key]) / len(bm_run[data_key]), np.std(bm_run[data_key])
            else:
                return None