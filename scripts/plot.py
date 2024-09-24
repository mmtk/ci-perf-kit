import plotly
from plotly.graph_objs import *
from datetime import timedelta, date
import parse
import numpy as np
import math


GRAPH_WIDTH = 500
GRAPH_HEIGHT_PER_BENCHMARK = 100

SHOW_DATA_POINT = False
TRACE_MODE = "lines+markers" if SHOW_DATA_POINT else "lines"

# Intervals between X values (dense for old data, sparse for recent data). See log_timeline()
X_INTERVAL_1 = 1
X_INTERVAL_2 = 3
X_INTERVAL_3 = 5

# We place the labels (big number/benchmark name/absolute number) on the position of (last point + this offset)
LABEL_OFFSET = X_INTERVAL_3 * 15
BIG_NUMBER_FONT_SIZE = 30
BM_NAME_FONT_SIZE = 15
BM_NAME_Y_SHIFT = 15
SHOW_ABS_NUMBER = False
ABS_NUMBER_FONT_SIZE = 10
ABS_NUMBER_FONT_Y_SHIFT = -30

# Plot statistics
PLOT_MOVING_AVERAGE = True
PLOT_STD_DEV = True

# Use the same Y range for all the traces
SAME_Y_RANGE_IN_ALL_TRACES = True

# runs: all the runs for a certain build (as a dictionary from run_id -> run results)
# plan: the plan to plot
# benchmarks: benchmarks to plot
# start_date, end_date: plot data between the given date range
# data_key: the data to render
# baseline: the baseline to plot as a dict {baseline: {benchmark: avg}}. None means no baseline, or no data for a certain benchmark.
# notes: a list of [date, note]. date is YYYYMMDD
def plot_history(build_info, runs, plan, benchmarks, start_date, end_date, data_key, baseline, notes=[]):
    layout = {
        "title": "%s - %s" % (build_info, plan),
        # "margin": {"t": 80},
        "width": GRAPH_WIDTH,
        "height": GRAPH_HEIGHT_PER_BENCHMARK * len(benchmarks),
    }
    
    n_benchmarks = len(benchmarks)
    if (n_benchmarks == 0):
        print("Unable to plot history for %s: no benchmark result found." % plan)
        exit(1)

    row = 1
    
    traces = []
    annotations = []
    baseline_hlines = []

    # we want all the traces use the same Y range so it is easier to interpret the plot. These two variables record the upper and lower of Y range
    y_range_upper = - float("inf")
    y_range_lower = float("inf")

    benchmarks.sort()

    aligned_notes = []
    for bm in benchmarks:
        # extract results
        print("Plotting %s %s..." % (plan, bm))

        is_last_row = row == n_benchmarks

        y, std = history_per_run(runs, plan, bm, data_key)
        x = log_timeline(len(y))
        x_labels = list(runs.keys())
        # We have to sort by date, run_id includes the machine name, we cannot sort by alphabet
        x_labels.sort(key = lambda x: parse.parse_run_date(x))

        n_points = len(x)
        assert len(y) == n_points
        assert len(std) == n_points
        assert len(x_labels) == n_points

        attributes = split_epochs(x, x_labels, y, std, notes.copy())
        # print(attributes)

        y_cur_aboslute = y[-1]

        # From now, all y's are normalized to this baseline
        if len(y) == 1:
            if y[0] != 0:
                nonzero_y = y
            else:
                nonzero_y = []
        else:
            nonzero_y = [i for i in y[:-1] if i != 0] # we dont want 0 as baseline, and we should not use the most recent data as baseline

        if len(nonzero_y) == 0:
            # We do not have any valid data for the benchmark
            # Find our baseline, and use it as the y_baseline.
            baseline_perf = 0
            if baseline is not None:
                for build in baseline:
                    if bm in baseline[build] and baseline[build][bm] is not None:
                        baseline_perf = baseline[build][bm]
                        if baseline_perf != 0:
                            break
            # We don't even have a baseline number for it. Just use 1 (random number)
            if baseline_perf == 0:
                baseline_perf = 1
            nonzero_y = [baseline_perf]

        # normalize to the min value in the latest epoch
        current_epoch = sorted(attributes.keys())[-1]
        y_baseline = attributes[current_epoch]['min']
        # No min value. There is no value in the plot at all. We just need a reasonable baseline.
        if y_baseline == 0:
            y_baseline = min(nonzero_y)
        # y_max = max(nonzero_y) / y_baseline
        # y_min = min(nonzero_y) / y_baseline

        this_y_upper = attributes[current_epoch]['max'] / y_baseline
        this_y_lower = attributes[current_epoch]['min'] / y_baseline
        this_y_lower_std = attributes[current_epoch]['min_std'] / y_baseline
        if this_y_lower == 0:
            this_y_lower = 1
            this_y_lower_std = 0

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

        # history
        traces.append({**history_trace, **{
            "line": {"width": 3, "color": "black"},
            "y": make_zero_as_none(y),
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
            "range": [this_y_lower - 0.02, this_y_upper + 0.02]
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
        def keep_first_in_index_range(arr, f, start, end):
            ret = []
            first = True
            for idx, x in enumerate(arr):
                if idx < start or idx >= end:
                    ret.append(None)
                elif f(x) and first:
                    ret.append(x)
                    first = False
                else:
                    ret.append(None)
            return ret

        # Mark epoch
        for epoch_name, v in attributes.items():
            print(v)

            # Epoch start
            epoch_start_y = keep_first_in_index_range(y, lambda y: y == v['start_y'] / y_baseline, v['start'], v['end'])

            assert v['start'] <= n_points
            assert v['end'] <= n_points

            # Normalized y
            epoch_normalized_start_y = v['start_y'] / y_baseline
            epoch_normalized_start_y_std = v['start_y_std'] / y_baseline
            epoch_normalized_end_y = v['end_y'] / y_baseline
            epoch_normalized_end_y_std = v['end_y_std'] / y_baseline

            # Epoch min/max
            epoch_normalized_min_y = v['min'] / y_baseline
            epoch_normalized_max_y = v['max'] / y_baseline

            regress = check_regression(epoch_normalized_start_y, epoch_normalized_start_y_std, epoch_normalized_end_y, epoch_normalized_end_y_std)
            if regress == "regression":
                epoch_color = "red"
            else:
                epoch_color = "green"

            traces.append({**history_trace, **{
                "hoverinfo": 'text',
                "mode": "markers",
                "textposition": "top center",
                "y": epoch_start_y,
                "text": "Epoch: %s<br />  start: %.2f ± %.2f, end: %.2f ± %.2f<br />  min: %.2f, max: %.2f" % (v['note'], epoch_normalized_start_y, epoch_normalized_start_y_std, epoch_normalized_end_y, epoch_normalized_end_y_std, epoch_normalized_min_y, epoch_normalized_max_y),
                "textfont_color": epoch_color,
                "cliponaxis": False,
                "marker": { "size": 10, "color": epoch_color, "symbol": "star-diamond"},
                "showlegend": False,
            }})

            # if epoch_name == current_epoch:
            #     # Epoch min
            #     traces.append({**history_trace, **{
            #         "hoverinfo": "text",
            #         "mode": "markers",
            #         "textposition": "top center",
            #         "y": keep_first_in_index_range(y, lambda y: y == epoch_normalized_min_y, v['start_x'], v['end_x'] + 1),
            #         "text": ["%s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
            #         "textfont_color": "green",
            #         "cliponaxis": False,
            #         "marker": { "size": 10, "color": "green", "symbol": "triangle-down" },
            #         "showlegend": False,
            #     }})
            #     # Epoch max
            #     traces.append({**history_trace, **{
            #         "hoverinfo": "text",
            #         "mode": "markers",
            #         "textposition": "top center",
            #         "y": keep_first_in_index_range(y, lambda y: y == epoch_normalized_max_y, v['start_x'], v['end_x'] + 1),
            #         "text": ["%s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
            #         "textfont_color": "red",
            #         "cliponaxis": False,
            #         "marker": { "size": 10, "color": "red", "symbol": "triangle-up" },
            #         "showlegend": False,
            #     }})

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
        # print(annotation)

        # highlight current
        current = y[-1]
        current_std = std[-1]
        # determine if current is improvement or degradation
        # print("cur: %.2f, std: %.2f, best: %.2f" % (current, current_std, y_best))
        if current == 0:
            # No data. Show neutral
            current_color = "black"
            current_symbol = "~"
        else:
            trend = check_regression(this_y_lower, this_y_lower_std, current, current_std)
            if trend == "improvment":
                current_color = "green"
                current_symbol = "▽"
            elif trend == "regression":
                # degradation
                current_color = "red"
                current_symbol = "△"
            else:
                # neutral
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
            "font": {"color": current_color, "size": BIG_NUMBER_FONT_SIZE},
            "xanchor": "center",
            "yanchor": "middle",
        }})
        # benchmark name
        annotations.append({**annotation, **{
            "text": "<b>%s" % bm,
            "font": {"color": "black", "size": BM_NAME_FONT_SIZE},
            "xanchor": "center",
            "yanchor": "bottom",
            "yshift": BM_NAME_Y_SHIFT
        }})
        # aboslute number
        if SHOW_ABS_NUMBER:
            annotations.append({**annotation, **{
                "text": "%.2f ms %s" % (y_cur_aboslute, current_symbol),
                "font": {"color": "black", "size": ABS_NUMBER_FONT_SIZE},
                "xanchor": "center",
                "yanchor": "bottom",
                "yshift": ABS_NUMBER_FONT_Y_SHIFT
            }})

        if PLOT_MOVING_AVERAGE:
            # moving average
            y_moving_average = moving_average(y, 10)
            traces.append({
                "name": bm,
                "hoverinfo": "none",
                # "fill": "tozeroy",
                "mode": TRACE_MODE,
                "line": {"width": 1, "color": "gray"},
                "type": "scatter",
                "x": x,
                "y": y_moving_average,
                "text": ["10-p moving avg: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, y_moving_average)],
                "xaxis": x_axis,
                "yaxis": y_axis,
                "showlegend": False,
            })

        if PLOT_STD_DEV:
            # variance (10p moving average of std dev)
            std_dev_moving_average = moving_average(std, 10)
            variance_trace = {
                "name": bm,
                "hoverinfo": "none",
                "mode": "lines",
                "line_color": "#cacccf",
                "line": {"width": 0},
                "x": x,
                "xaxis": x_axis,
                "yaxis": y_axis,
                "showlegend": False,
            }
            variance_down = list(map(lambda a, b: a - b if a is not None and b is not None else None, y_moving_average, std_dev_moving_average))
            traces.append({**variance_trace, **{
                # a hack: fill everything under this line the same as the background color
                "fill": "tozeroy",
                "line_color": "#e5ecf6",
                "y": variance_down,
                "text": ["moving avg - std dev: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, variance_down)],
            }})
            variance_up = list(map(lambda a, b: a + b if a is not None and b is not None else None, y_moving_average, std_dev_moving_average))
            traces.append({**variance_trace, **{
                # fill things in grey between this trace and the trace above
                "fill": "tonexty",
                "y": variance_up,
                "text": ["moving avg + std dev: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, variance_up)],
            }})

        # baseline - we will draw one horizontal line per each baseline
        baseline_opacity = 0.6
        baseline_color = "orange"
        baseline_trace = {
            "hoverinfo": "text",
            "mode": "lines",
            "line": {"width": 1, "color": baseline_color, "dash": "dash"},
            "x": x,
            "xaxis": x_axis,
            "yaxis": y_axis,
            "showlegend": False,
            "opacity": baseline_opacity,
        }
        baseline_label = {
            "xref": x_axis,
            "yref": y_axis,
            "x": x[0],
            "font": {"color": baseline_color, "size": 12},
            "showarrow": False,
            "xanchor": "center",
            "yanchor": "top",
            "opacity": baseline_opacity,
        }
        if baseline is not None:
            for build in baseline:
                if bm in baseline[build] and baseline[build][bm] is not None:
                    # normalize and update y range
                    hline = baseline[build][bm] / y_baseline
                    if hline > y_range_upper:
                        y_range_upper = hline
                    if hline < y_range_lower:
                        y_range_lower = hline

                    print("%s baseline %s: %s" % (bm, build, hline))

                    traces.append({**baseline_trace, **{
                        "y": [hline] * len(x),
                        "text": "%s: %.2f" % (build, hline),
                    }})
                    # annotations.append({**baseline_label, **{
                    #     "y": hline,
                    #     "text": "%s: %.2f" % (build, hline),
                    # }})

        # Notes
        # Somehow this line does not show. But it adds a hover text for all the plots.
        # for note in aligned_notes:
        #     note_trace = {
        #         "hoverinfo": "text",
        #         "mode": "lines",
        #         "line": {"width": 10, "color": "blue"},
        #         "x": [note['x']],
        #         "y": [0, 999],
        #         "xaxis": x_axis,
        #         "yaxis": y_axis,
        #         "showlegend": False,
        #         "opacity": 0,
        #         "text": note['note']
        #     }
        #     traces.append(note_trace)

        row += 1

    # fix range for all the traces
    if SAME_Y_RANGE_IN_ALL_TRACES:
        RANGE_EXTRA = 0.2
        y_range = [y_range_lower - RANGE_EXTRA, y_range_upper + RANGE_EXTRA]
        for i in range(1, row):
            layout["yaxis%d" % i]["range"] = y_range

    fig = Figure(data = Data(traces), layout = layout)
    for anno in annotations:
        fig.add_annotation(anno)
    for line in baseline_hlines:
        fig.add_shape(line)
    # This plots a vertical line for each note in the first subgraph.
    # for note in aligned_notes:
    #     fig.add_vline(x = int(note['x']), line_color = 'blue', annotation = { "text": "📓", "hovertext": note['note'] })

    fig.update_layout(hovermode='x')
    fig.update_layout(margin=dict(l=5, r=5, t=50, b=5))

    return fig


def split_epochs(x, x_labels, y, y_std, notes):
    import datetime

    FIRST_EPOCH = "19700101"

    attrs = {}
    epoch = None

    def new_epoch(idx, epoch_name, note = None):
        nonlocal epoch

        # End previous epoch
        if epoch is not None:
            if idx > 1:
                prev_epoch_end = idx - 1
            else:
                prev_epoch_end = 0
            attrs[epoch]['end'] = prev_epoch_end
            attrs[epoch]['end_y'] = y[prev_epoch_end]
            attrs[epoch]['end_y_std'] = y_std[prev_epoch_end]

        epoch = epoch_name

        attrs[epoch_name] = {}
        attrs[epoch_name]['epoch'] = epoch_name
        attrs[epoch_name]['start'] = idx
        attrs[epoch_name]['start_y'] = y[idx]
        attrs[epoch_name]['start_y_std'] = y_std[idx]
        if note is not None:
            attrs[epoch_name]['note'] = note
        else:
            attrs[epoch_name]['note'] = epoch_name

    # Sort notes
    notes.sort(key = lambda x: parse.parse_note_date(x['date'], x['time']))

    # Align notes to logs/run_ids. Each note has a date, find the next log on or after the date.
    def peek_next_note_date():
        return parse.parse_note_date(notes[0]['date'], notes[0]['time']) if len(notes) > 0 else datetime.datetime(9999, 1, 1) # end of the world. We will never find a log after this date.
    next_note_date = peek_next_note_date()


    for idx, run_id in enumerate(x_labels):
        log_date = parse.parse_run_date(run_id)
        if log_date >= next_note_date:
            # We may have multiple notes on this date. We have to combine them.
            combined_note = None

            while log_date >= next_note_date:
                note = notes.pop(0)
                if combined_note is None:
                    combined_note = { 'run_id': run_id, 'note': f"{note['date']}: {note['note']}" }
                else:
                    combined_note['note'] += f",{note['date']}: {note['note']}"
                next_note_date = peek_next_note_date()
            new_epoch(idx, note['date'], combined_note['note'])

        if epoch is None:
            new_epoch(idx, FIRST_EPOCH)

    # End the last epoch
    attrs[epoch]['end'] = len(x) - 1
    attrs[epoch]['end_y'] = y[-1]
    attrs[epoch]['end_y_std'] = y_std[-1]

    # For each epoch, find min/max
    for name, epoch in attrs.items():
        def find_min_with_index(lst, start, end):
            if not lst:
                raise ValueError("The list is empty")

            if start < 0 or end >= len(lst) or start > end:
                print("start %d, end %d, len %d", start, end, len(lst))
                raise IndexError("Invalid start or end index")

            min_value = lst[start]
            min_index = start

            for i in range(start + 1, end + 1):
                if lst[i] < min_value:
                    min_value = lst[i]
                    min_index = i

            return min_value, min_index
        def find_max_with_index(lst, start, end):
            if not lst:
                raise ValueError("The list is empty")

            if start < 0 or end >= len(lst) or start > end:
                print("start %d, end %d, len %d", start, end, len(lst))
                raise IndexError("Invalid start or end index")

            max_value = lst[start]
            max_index = start

            for i in range(start + 1, end + 1):
                if lst[i] > max_value:
                    max_value = lst[i]
                    max_index = i

            return max_value, max_index

        min, min_idx = find_min_with_index(y, epoch['start'], epoch['end'])
        if min != 0:
            epoch['min'] = min
            epoch['min_std'] = y_std[min_idx]
        else:
            epoch['min'] = epoch['start_y']
            epoch['min_std'] = 0

        max, max_idx = find_max_with_index(y, epoch['start'], epoch['end'])
        if max != 0:
            epoch['max'] = max
            epoch['max_std'] = y_std[max_idx]
        else:
            epoch['max'] = epoch['start_y']
            epoch['max_std'] = 0

    return attrs

# Return improvement, or regression, or neutral
def check_regression(r1, std1, r2, std2):
    # Determine the lower and upper bounds for r1 and r2
    lower_bound_r1 = r1 - std1
    upper_bound_r1 = r1 + std1
    lower_bound_r2 = r2 - std2
    upper_bound_r2 = r2 + std2

    if upper_bound_r2 < lower_bound_r1:
        return "improvement"
    elif lower_bound_r2 > upper_bound_r1:
        return "regression"
    # Otherwise, it's neutral
    else:
        return "neutral"

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
            # We have to sort by date, run_id includes the machine name, we cannot sort by alphabet
            x_labels.sort(key = lambda x: parse.parse_run_date(x))

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

    zeroes_in_window = 0
    for i in range(0, n):
        if window_len < p:
            window_len += 1
        else:
            window_sum -= array_numbers[i - p]
            if array_numbers[i - p] == 0:
                zeroes_in_window -= 1

        if array_numbers[i] == 0:
            zeroes_in_window += 1

        window_sum += array_numbers[i]
        assert zeroes_in_window >= 0
        if window_len > zeroes_in_window:
            ma.append(window_sum / float(window_len - zeroes_in_window))
        else:
            ma.append(None)

    assert len(array_numbers) == len(ma)
    return ma


# Returns two arrays:
# The first array is average execution time for the benchmark on one day.
# The second array represents standard deviation.
# - This is no longer used.
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

        print("Run for %s: %s (%s ± %s)" % (single_date, last_run, result[0], result[1]))
        avg.append(result[0])
        std.append(result[1])
    
    return avg, std


def history_per_run(runs, plan, benchmark, data_key):
    # ordered runs
    run_ids = list(runs.keys())
    run_ids.sort(key = lambda x: parse.parse_run_date(x))

    avg = []
    std = []

    for rid in run_ids:
        result = average_time(runs[rid], plan, benchmark, data_key)
        if result is None:
            result = 0, 0
        
        # print("Run for %s: %s +/- %s" % (rid, result[0], result[1]))
        avg.append(result[0])
        std.append(result[1])

    return avg, std


# Use first non-zero value as 0, normalize each value to be a percentage compared to the first non-zero value
def normalize_history(arr):
    if (len(arr)) == 0:
        return arr

    # print(arr)
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


def make_zero_as_none(arr):
    return list(map(lambda x: x if x != 0 else None, arr))


# Given n points, return their x values (starting from 0) that are dense for the first few values and sparse for the last values.
# We could use exponential values, however, it does not look as good.
# Instead, we use fixed intervals:
# * [-10, -1]: 5 between points
# * [-30, -10): 3 between points
# * Others: 1
INTERVALS = [X_INTERVAL_2] * 20 + [X_INTERVAL_3] * 10
def log_timeline(n):
    if n == 0:
        return []

    if n <= 30:
        intervals = INTERVALS[-n:]
    else:
        intervals = INTERVALS.copy()
        intervals = [X_INTERVAL_1] * (n - 30) + intervals

    assert len(intervals) == n

    cur = 0
    x = []
    for i in range(0, n):
        x.append(cur)
        cur += intervals[i]

    assert len(x) == n
    return x


def average_time(run, plan, benchmark, data_key):
    for bm_run in run:
        # log name is something like this. We break it down into each flag.
        # cassandra.0.0.jdk-mmtk.ms.s.c2.tph.probes_cp.probes_rustmmtk.immix.dacapochopin-69a704e.log.gz
        # We will see if any flag matches the plan name.
        log_flags = [x.lower() for x in bm_run['log_name'].split(".")]
        # build string equals the plan
        # or build string ends with the plan
        # or plan in one of the log flags
        if bm_run['benchmark'] == benchmark and \
            (bm_run['build'].lower() == plan.lower() \
                or bm_run['build'].lower().endswith(plan.lower()) \
                or (plan.lower() in log_flags)):
            if data_key in bm_run and len(bm_run[data_key]) != 0:
                return sum(bm_run[data_key]) / len(bm_run[data_key]), np.std(bm_run[data_key])
            else:
                return None


# Given an array of results {benchmark, build, data (such as execution_times), log_name}, return a dict {build: {benchmark: avg}}
def calculate_baseline(baseline_results, baseline_builds, data_key):
    ret = {}
    for b in baseline_builds:
        avg_per_bm = {}
        for r in baseline_results:
            if r['build'] == b:
                if r[data_key] and len(r[data_key]) != 0:
                    avg = sum(r[data_key]) / len(r[data_key])
                else:
                    avg = None
                avg_per_bm[r['benchmark']] = avg
        ret[b] = avg_per_bm
    return ret


def get_excluded_runs_from_env_var(v):
    from os import environ
    excluded_runs = []
    if v in environ:
        print("exclude runs: %s" % environ[v])
        excluded_runs = environ[v].split(',')
    return excluded_runs
