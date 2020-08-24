import plotly
from plotly.graph_objs import *
from datetime import timedelta, date
import parse
import numpy as np
import math


GRAPH_WIDTH = 1000
GRAPH_HEIGHT_PER_BENCHMARK = 200

SHOW_DATA_POINT = False
TRACE_MODE = "lines+markers" if SHOW_DATA_POINT else "lines"

# runs: all the runs for a certain build (as a dictionary from run_id -> run results)
# plan: the plan to plot
# benchmarks: benchmarks to plot
# start_date, end_date: plot data between the given date range
def plot_history(runs, plan, benchmarks, start_date, end_date, data_key):
    layout = {
        "title": plan,
        # "margin": {"t": 80},
        "width": GRAPH_WIDTH,
        "height": GRAPH_HEIGHT_PER_BENCHMARK * len(benchmarks),
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

        is_last_row = row == n_benchmarks

        # We place the labels (big number/benchmark name/absolute number) on the position of (last point + this offset)
        LABEL_OFFSET = 3

        y, std = history_per_run(runs, plan, bm, data_key)
        x = list(range(0, len(y)))
        print(x)
        x_labels = list(runs.keys())
        x_labels.sort()

        y_cur_aboslute = y[-1]

        # From now, all y's are normalized to this baseline
        nonzero_y = [i for i in y[:-1] if i != 0] # we dont want 0 as baseline, and we should not use the most recent data as baseline
        y_baseline = min(nonzero_y)
        y_max = max(nonzero_y) / y_baseline
        y_min = min(nonzero_y) / y_baseline

        this_y_upper = max(y) / y_baseline
        this_y_lower = min(y) / y_baseline

        # update range
        if this_y_upper > y_range_upper:
            y_range_upper = this_y_upper
        if this_y_lower < y_range_lower:
            y_range_lower = this_y_lower

        # normalize y
        y = normalize_to(y, y_baseline)
        std = normalize_to(std, y_baseline)

        x_axis = "x"
        y_axis = "y%d" % row

        # history
        history_trace = {
            "name": bm,
            "hoverinfo": "text",
            "mode": TRACE_MODE,
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
            # attempt to show xticks. Couldn't get this work. Xticks are shown under the first subgraph. 
            # I can't switch it to the last (or it does not show on the last because out of boundary)
            # "showticklabels": is_last_row,
            # "tickmode": "array",
            # "tickvals": list(range(0, len(y))),
            # "ticktext": x_labels,
            "showticklabels": False,
            "anchor": x_axis,
            "domain": [0, 1],
            "mirror": False,
            "showgrid": False,
            "showline": False,
            "zeroline": False,
        }
        # e.g. if we have 4 rows (row = 5 at the moment)
        # the y domain for each trace should be [0, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1]
        ydomain = [1 - 1/n_benchmarks * row, 1 - 1/n_benchmarks * (row - 1)]
        layout["yaxis%d" % row] = {
            "ticks": "",
            "anchor": x_axis,
            "domain": ydomain,
            "mirror": False,
            "showgrid": False,
            "showline": True,
            "zeroline": False,
            "showticklabels": False,
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
            "hoverinfo": "none",
            "mode": "markers+text",
            "textposition": "top center",
            "y": y_max_array,
            "text": ["%s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
            "textfont_color": "red",
            "cliponaxis": False,
            "marker": { "size": 20, "color": "red", "symbol": "triangle-up" },
            "showlegend": False,
        }})
        y_min_array = keep_first(y, lambda x: x == y_min) # keep min, leave others as None
        traces.append({**history_trace, **{
            "hoverinfo": "none",
            "mode": "markers+text",
            "textposition": "bottom center",
            "y": y_min_array,
            "text": ["%s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
            "textfont_color": "green",
            "cliponaxis": False,
            "marker": { "size": 20, "color": "green", "symbol": "triangle-down" },
            "showlegend": False,
        }})

        # labeling
        annotation = {
            "xref": x_axis,
            "yref": y_axis,
            "x": x[-1] + LABEL_OFFSET,
            "y": 1,
            "showarrow": False,
            # "bordercolor": 'black',
            # "borderwidth": 1,
        }
        print(annotation)

        # highlight current
        current = y[-1]
        current_std = std[-1]
        # determine if current is improvement or degradation
        if current + current_std < y_min:
            # improvement
            current_color = "green"
            current_symbol = "▽"
        elif current - current_std > y_min:
            # degradation
            current_color = "red"
            current_symbol = "△"
        else:
            # none of the above
            current_color = "black"
            current_symbol = "~"

        y_last_array = keep_last(y, lambda x: x == current)
        traces.append({**history_trace, **{
            "hoverinfo": "none",
            "mode": "markers",
            "y": y_last_array,
            "text": ["history current: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
            "marker": {"size": 15, "color": "black"},
            "showlegend": False,
        }})
        # big number
        annotations.append({**annotation, **{
            "text": "%.2f" % current,
            "font": {"color": current_color, "size": 60},
            "xanchor": "center",
            "yanchor": "middle",
        }})
        # benchmark name
        annotations.append({**annotation, **{
            "text": "<b>%s" % bm,
            "font": {"color": "black", "size": 20},
            "xanchor": "center",
            "yanchor": "bottom",
            "yshift": 40
        }})
        # aboslute number
        annotations.append({**annotation, **{
            "text": "%.2f ms %s" % (y_cur_aboslute, current_symbol),
            "font": {"color": "black"},
            "xanchor": "center",
            "yanchor": "bottom",
            "yshift": -50
        }})

        # moving average
        y_moving_average = moving_average(y, 10)
        traces.append({
            "name": bm,
            "hoverinfo": "text",
            # "fill": "tozeroy",
            "mode": TRACE_MODE,
            "line": {"width": 1, "color": "gray"},
            "type": "scatter",
            "x": x,
            "y": y_moving_average,
            "text": ["10-p moving avg: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y_moving_average)],
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
        })

        # variance (10p moving average of std dev)
        std_dev_moving_average = moving_average(std, 10)
        variance_trace = {
            "name": bm,
            "hoverinfo": "text",
            "mode": "lines",
            "line_color": "#cacccf",
            "line": {"width": 0},
            "x": x,
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
        }
        variance_up = list(map(lambda a, b: a + b, y_moving_average, std_dev_moving_average))
        traces.append({**variance_trace, **{
            "y": variance_up,
            "text": ["moving avg + std dev: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, variance_up)],
        }})
        variance_down = list(map(lambda a, b: a - b, y_moving_average, std_dev_moving_average))
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
        "width": GRAPH_WIDTH,
        "height": GRAPH_HEIGHT_PER_BENCHMARK * len(benchmarks),
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