import plotly
from plotly.graph_objs import *
from datetime import timedelta, date
import parse
import numpy as np
import math


GRAPH_WIDTH = 500
GRAPH_HEIGHT_PER_BENCHMARK = 100

# Compact "sparkline" sizing, used for the dashboard thumbnail rendered for index.html
# (see the `sparkline` param on plot_history). No title, no decorative traces (moving
# average/std-dev band/epoch markers/baseline lines) - just the colored history line,
# the current-value number, and the informational mutator/STW overlay lines.
SPARKLINE_GRAPH_WIDTH = 300
SPARKLINE_HEIGHT_PER_BENCHMARK = 40
SPARKLINE_BIG_NUMBER_FONT_SIZE = 13
SPARKLINE_BM_NAME_FONT_SIZE = 9
SPARKLINE_BM_NAME_Y_SHIFT = 6
SPARKLINE_CURRENT_POINT_MARKER_SIZE = 4
SPARKLINE_MARGIN = {"l": 2, "r": 2, "t": 2, "b": 2}
FULL_MARGIN = {"l": 5, "r": 5, "t": 50, "b": 5}

SHOW_DATA_POINT = False
TRACE_MODE = "lines+markers" if SHOW_DATA_POINT else "lines"

# Chart chrome/ink, from the dataviz palette (references/palette.md): a light,
# consistent surface instead of Plotly's default theme.
SURFACE = "#fcfcfb"
GRIDLINE = "#e1e0d9"
AXIS_LINE = "#c3c2b7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
FONT_FAMILY = "system-ui, -apple-system, 'Segoe UI', sans-serif"

# Status colors (fixed, never themed) - used for the regression/improvement/neutral
# coloring of the total-time history line and current-value number.
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
STATUS_NEUTRAL = INK_MUTED

# Reference line for each baseline build (e.g. jdk-g1, jdk-zgc) - categorical slot 2.
BASELINE_COLOR = "#eb6834"

# Informational overlay lines shown alongside total time on the same per-benchmark
# row: (data_key, display label, line color). These are plotted plain - no
# regression coloring, no big number, no moving average/std-dev band - since total
# time is what's being watched for regressions; mutator/STW are context only. Colored
# in gray (not a hue) so they read as secondary to total time's own green/red/gray
# regression coloring - mutator (the larger, more prominent component of total time)
# a darker gray, STW a lighter one.
SECONDARY_METRICS = [
    ("time.other", "Mutator time", "#5c5a54"),  # darker gray - the more prominent secondary metric
    ("time.stw", "STW time", "#b0aca2"),  # lighter gray
]

# Intervals between X values (dense for old data, sparse for recent data). See log_timeline()
X_INTERVAL_1 = 1
X_INTERVAL_2 = 3
X_INTERVAL_3 = 5

# We place the labels (big number/benchmark name/absolute number) on the position of (last point + this offset)
LABEL_OFFSET = X_INTERVAL_3 * 15
# A tighter offset for sparkline mode - the full offset leaves most of a
# compact dashboard card blank (it's sized for a much wider chart).
SPARKLINE_LABEL_OFFSET = X_INTERVAL_3 * 4
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
Y_RANGE_EXTRA = 0.2

MIN_MAX_MARKER_SIZE = 5
CURRENT_POINT_MARKER_SIZE = 10

# Shared core of a green(improvement)/red(regression)/gray(neutral) history line:
# split into epochs, pick the current epoch's own minimum as the baseline, normalize
# to it, and classify each point/segment against the best value seen so far in its
# epoch (see split_epochs/check_regression). This is plot_history's per-benchmark
# computation for its one primary series (time.total for the time chart, latency.p50
# for the latency chart - see history_report.py) - factored out from the trace-
# building below it since the computation itself has no UI concerns.
#
# y, std: this series' raw values, one per x/x_labels entry (see history_per_run).
# x, x_labels: the shared run timeline/run_ids (see log_timeline) - same order as y/std.
# notes: config notes (epoch boundaries) - copied internally, since split_epochs
#   consumes (pops from) whatever list it's given.
# no_data_fallback_perf: baseline to fall back to if this series has no valid nonzero
#   value to normalize against (nothing at all, or only the current/most-recent point
#   is nonzero) - resolved from plot_history's `baseline` dict (stock JDK data) for the
#   time chart; the latency chart has no equivalent, so it just uses the default of 1.
#
# Returns a dict:
#   y_norm, std_norm, y_plot: y/std normalized to y_baseline (y_plot has zeros -> None)
#   y_baseline: the raw value that normalizes to 1.0
#   nonzero_y: the nonzero raw values used to resolve y_baseline (see
#     no_data_fallback_perf) - exposed for callers that size a plot element (e.g. an
#     epoch divider) to the series' overall visible range
#   attrs, current_epoch: split_epochs() output, for the caller's own epoch decorations
#   this_y_upper, this_y_lower, this_y_lower_std: current epoch's normalized bounds
#   seg_colors, seg_colors_info: per-point color (green/red/STATUS_NEUTRAL) and
#     best-so-far comparison info, aligned with y (see split_epochs's line_colors)
#   current, current_std: the latest (current) point's normalized value/std
#   current_trend: "improvement"/"regression"/"neutral", or None if the current
#     point has no data at all
def compute_regression_series(y, std, x, x_labels, notes, no_data_fallback_perf=1):
    attrs = split_epochs(x, x_labels, y, std, notes.copy())
    current_epoch = sorted(attrs.keys())[-1]

    if len(y) == 1:
        nonzero_y = [y[0]] if y[0] != 0 else []
    else:
        # we dont want 0 as baseline, and we should not use the most recent data as baseline
        nonzero_y = [v for v in y[:-1] if v != 0]
    if len(nonzero_y) == 0:
        nonzero_y = [no_data_fallback_perf]

    y_baseline = attrs[current_epoch]['min']
    # No min value in the current epoch. We just need a reasonable baseline.
    if y_baseline == 0:
        y_baseline = min(nonzero_y)

    this_y_upper = attrs[current_epoch]['max'] / y_baseline
    this_y_lower = attrs[current_epoch]['min'] / y_baseline
    this_y_lower_std = attrs[current_epoch]['min_std'] / y_baseline
    if this_y_lower == 0:
        this_y_lower = 1
        this_y_lower_std = 0

    y_norm = normalize_to(y, y_baseline)
    std_norm = normalize_to(std, y_baseline)

    seg_colors = []
    seg_colors_info = []
    for epoch_name in sorted(attrs.keys()):
        seg_colors.extend(attrs[epoch_name]['line_colors'])
        seg_colors_info.extend(attrs[epoch_name]['line_colors_info'])

    current = y_norm[-1]
    current_std = std_norm[-1]
    current_trend = None if y[-1] == 0 else check_regression(this_y_lower, this_y_lower_std, current, current_std)

    return {
        'y_norm': y_norm,
        'std_norm': std_norm,
        'y_plot': make_zero_as_none(y_norm),
        'y_baseline': y_baseline,
        'nonzero_y': nonzero_y,
        'attrs': attrs,
        'current_epoch': current_epoch,
        'this_y_upper': this_y_upper,
        'this_y_lower': this_y_lower,
        'this_y_lower_std': this_y_lower_std,
        'seg_colors': seg_colors,
        'seg_colors_info': seg_colors_info,
        'current': current,
        'current_std': current_std,
        'current_trend': current_trend,
    }


# The colored-segment traces for one regression-classified line (see
# compute_regression_series) - deliberately stops one point short of the end; the
# very last point's status is conveyed by the caller's own current-value indicator
# (a big number annotation or a small marker) instead.
def regression_segment_traces(base_trace, x, y_plot, seg_colors, line_width):
    return [
        {**base_trace, **{
            "x": x[i:i+2],
            "y": y_plot[i:i+2],
            "line": {"width": line_width, "color": seg_colors[i+1]},
        }}
        for i in range(0, len(x) - 2)
    ]


# runs: all the runs for a certain build (as a dictionary from run_id -> run results)
# plan: the plan to plot
# benchmarks: benchmarks to plot
# start_date, end_date: plot data between the given date range
# data_key: the data to render (the metric that drives regression coloring/the big number
#   - "time.total" for the time chart, "latency.p50" for the latency chart)
# baseline: the baseline to plot as a dict {baseline: {benchmark: avg}}. None means no
#   baseline, or no data for a certain benchmark - the latency chart has no equivalent,
#   so it always passes None.
# notes: a list of [date, note]. date is YYYYMMDD
# sparkline: render a compact, chrome-free version (no title, no moving average/std-dev
#   band, no epoch/baseline lines, smaller fonts) for use as a dashboard thumbnail.
#   secondary_metrics are still overlaid, just without a legend.
# secondary_metrics: informational overlay lines plotted alongside the primary series on
#   the same row - plain (no regression coloring, no big number, no moving average/std-
#   dev band), as a list of (data_key, display label, line color). Defaults to
#   SECONDARY_METRICS (mutator/STW time) when None - the latency chart passes
#   LATENCY_SECONDARY_METRICS (p90/p99/p99.9/p99.99) instead, with data_key="latency.p50"
#   as the primary series that drives the big number/regression coloring - i.e. the exact
#   same chart, just with different Ys (see history_report.py).
# title_suffix: the parenthetical in the chart title, e.g. "(Total / Mutator / STW)".
# primary_label: how the primary series is named in secondary_metrics' hover text ("X%
#   of <primary_label>") - "total" for the time chart, "p50" for the latency chart.
# secondary_clamp: whether secondary_metrics are clamped to the primary series' own epoch
#   range (and excluded from the shared cross-benchmark Y range) - appropriate when a
#   secondary metric is inherently <= the primary one (mutator/STW are always <= total),
#   but not for latency, where p90+ are routinely many times p50 and clamping them would
#   flatten them into invisible lines pinned at the top of p50's own range.
# only_benchmarks_with_data: skip benchmarks with no nonzero value anywhere in their
#   history for data_key or any secondary_metrics key - appropriate for the latency chart,
#   where only request/response-style benchmarks (cassandra, h2, lusearch, tomcat, ...)
#   report latency at all, unlike time.total which every benchmark always has.
# data_label, unit: how the primary series is named/units in hover text - "Total time"/
#   "ms" for the time chart, "p50 latency"/"usec" for the latency chart. Also used for
#   secondary_metrics' hover text (same unit, using each metric's own display label).
# secondary_show_percentage: whether secondary_metrics' hover text includes "X% of
#   <primary_label>" - meaningful for the time chart (mutator + STW make up total time)
#   but not the latency chart (p90 isn't "part of" p50 the way mutator is part of total).
# log_y: log-scale Y axis - off for the time chart (values normalized close to 1 with
#   secondary_clamp keep it readable on a linear axis); on for the latency chart, whose
#   unclamped secondary percentiles can span two-plus orders of magnitude.
def plot_history(build_info, runs, plan, benchmarks, start_date, end_date, data_key, baseline, notes=[], run_commit_info=None, sparkline=False,
                  secondary_metrics=None, title_suffix="(Time)", primary_label="total",
                  secondary_clamp=True, only_benchmarks_with_data=False,
                  data_label="Total time", unit="ms", secondary_show_percentage=True, log_y=False):
    graph_width = SPARKLINE_GRAPH_WIDTH if sparkline else GRAPH_WIDTH
    height_per_benchmark = SPARKLINE_HEIGHT_PER_BENCHMARK if sparkline else GRAPH_HEIGHT_PER_BENCHMARK
    big_number_font_size = SPARKLINE_BIG_NUMBER_FONT_SIZE if sparkline else BIG_NUMBER_FONT_SIZE
    bm_name_font_size = SPARKLINE_BM_NAME_FONT_SIZE if sparkline else BM_NAME_FONT_SIZE
    bm_name_y_shift = SPARKLINE_BM_NAME_Y_SHIFT if sparkline else BM_NAME_Y_SHIFT
    current_point_marker_size = SPARKLINE_CURRENT_POINT_MARKER_SIZE if sparkline else CURRENT_POINT_MARKER_SIZE
    label_offset = SPARKLINE_LABEL_OFFSET if sparkline else LABEL_OFFSET

    secondary_metrics = SECONDARY_METRICS if secondary_metrics is None else secondary_metrics

    if only_benchmarks_with_data:
        data_keys = [data_key] + [k for k, _, _ in secondary_metrics]
        def _has_any_data(bm):
            return any(
                any(v != 0 for v in history_per_run(runs, plan, bm, k)[0])
                for k in data_keys
            )
        benchmarks = [bm for bm in benchmarks if _has_any_data(bm)]
        if len(benchmarks) == 0:
            print("No benchmark has data for %s in plan %s yet." % (data_key, plan))
            return None

    layout = {
        "width": graph_width,
        "height": height_per_benchmark * len(benchmarks),
        "font": {"family": FONT_FAMILY, "color": INK_PRIMARY},
        "plot_bgcolor": SURFACE,
        "paper_bgcolor": SURFACE,
    }
    if not sparkline:
        layout["title"] = {
            "text": "%s - %s %s" % (build_info, plan, title_suffix),
            "font": {"size": 16, "color": INK_PRIMARY},
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

    epoch_vlines = []

    # Only show the (rare, one-time) legend entry for each secondary/informational
    # metric once, on the first benchmark row that actually has data for it.
    secondary_legend_shown = {key: False for key, _, _ in secondary_metrics}

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

        # Commit info (if any) for the datapoint hover text only, rendered on
        # its own line (deliberately kept separate from x_labels, which is
        # used for date-sorting/matching - splicing a commit hash into that
        # could spuriously match the run-id-date regex).
        commit_info_lines = [
            parse.format_commit_info_line((run_commit_info or {}).get(rid))
            for rid in x_labels
        ]

        y_cur_aboslute = y[-1]
        y_raw = y

        # We do not have any valid data for the benchmark: find our baseline, and use
        # it as the fallback baseline (see compute_regression_series).
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

        series = compute_regression_series(y, std, x, x_labels, notes, no_data_fallback_perf=baseline_perf)

        attributes = series['attrs']
        current_epoch = series['current_epoch']
        y_baseline = series['y_baseline']
        y_max = max(series['nonzero_y']) / y_baseline
        y_min = min(series['nonzero_y']) / y_baseline
        this_y_upper = series['this_y_upper']
        this_y_lower = series['this_y_lower']
        this_y_lower_std = series['this_y_lower_std']

        # update range
        if this_y_upper > y_range_upper:
            y_range_upper = this_y_upper
        if this_y_lower < y_range_lower:
            y_range_lower = this_y_lower

        # normalize y
        y = series['y_norm']
        std = series['std_norm']

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
        history_x = x
        history_y = series['y_plot']
        history_colors = series['seg_colors']
        line_colors_info = series['seg_colors_info']

        assert len(history_colors) == len(history_x)
        assert len(history_colors) == len(history_y)
        assert len(history_colors) == len(line_colors_info)

        # render each segment with color
        traces.extend(regression_segment_traces(history_trace, history_x, history_y, history_colors, 3))

        # render the hovertext with an invisible trace (we have to do this otherwise the hovertext is fucked up -- the segments are too crowded and we would see multiple hover texts showing up)
        # Three lines: run id, commit info (if any - skipped otherwise), then the data
        # label/normalized value/status and the absolute value (with unit).
        history_hovertext = []
        for (rid, commit_info_line, raw_val, val, color_info) in zip(x_labels, commit_info_lines, y_raw, y, line_colors_info):
            lines = [rid]
            if commit_info_line:
                lines.append(commit_info_line)
            if color_info is None:
                lines.append("%s: no data" % data_label)
            else:
                lines.append("%s: %s (%s), %s %s" % (data_label, get_value_text(val), color_info['regression'], get_value_text(raw_val), unit))
            history_hovertext.append("<br \>".join(lines))
        if not sparkline:
            # Static PNG export has no hover, so skip this trace there.
            traces.append({**history_trace, **{
                "line": { "color": INK_PRIMARY },
                "y": history_y,
                "opacity": 0,
                "text": history_hovertext,
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
        # Plotly's axis "range" must be given in log10 units when type="log" (unlike
        # every trace's own y-values, which are always given in normal/linear units
        # regardless of axis type - see the SAME_Y_RANGE_IN_ALL_TRACES block below,
        # which keeps a separate linear-space range for trace data like epoch_vlines).
        if log_y:
            row_range = [math.log10(this_y_lower / 1.3), math.log10(this_y_upper * 1.3)]
        else:
            row_range = [this_y_lower - Y_RANGE_EXTRA, this_y_upper + Y_RANGE_EXTRA]
        layout["yaxis%d" % row] = {
            "ticks": "",
            "anchor": x_axis,
            "domain": ydomain,
            "mirror": False,
            "showgrid": False,
            "showline": not sparkline,
            "linecolor": AXIS_LINE,
            "zeroline": False,
            "showticklabels": False,
            "type": "log" if log_y else "linear",
            "range": row_range,
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
        def find_first_in_index_range(arr, v, start, end):
            for idx, x in enumerate(arr):
                if idx < start:
                    continue
                if idx >= end:
                    return None
                if x == v:
                    return idx
            return None

        # labeling - anchored at data value 1 (the baseline) by default, which reads
        # fine when the row's Y range stays close to 1 (time's mutator/STW overlay is
        # always <= total, so it never stretches the range much). secondary_clamp=False
        # rows (latency) can have a Y range dozens of times wider than 1 (p9999 vs.
        # p50), which would leave data-anchored annotations stranded near the bottom -
        # so those anchor to a fixed fraction of the row's own domain instead, which
        # stays put regardless of how wide the data range is.
        if secondary_clamp:
            annotation = {
                "xref": x_axis,
                "yref": y_axis,
                "x": x[-1] + label_offset,
                "y": 1,
                "showarrow": False,
            }
        else:
            # Plotly's annotation yref validator wants the bare axis name for the
            # first axis ("y domain", not "y1 domain") when using domain reference,
            # unlike trace yaxis assignment (which does accept "y1").
            domain_yref = "y domain" if y_axis == "y1" else "%s domain" % y_axis
            annotation = {
                "xref": x_axis,
                "yref": domain_yref,
                "x": x[-1] + label_offset,
                "y": 0.5,
                "showarrow": False,
            }

        # highlight current
        current = series['current']
        current_std = series['current_std']
        trend = series['current_trend']
        if trend is None:
            # No data. Show neutral
            current_color = STATUS_NEUTRAL
            current_symbol = "~"
        else:
            current_color = get_regression_color(trend)
            current_symbol = get_regression_symbol(trend)

        y_last_array = keep_last(y, lambda x: x == current)
        traces.append({**history_trace, **{
            "hoverinfo": "none",
            "mode": "markers",
            "y": y_last_array,
            "text": ["history current: %s: %.2f" % (x, y) for (x, y) in zip(x_labels, y)],
            "marker": {"size": current_point_marker_size, "color": INK_PRIMARY},
            "showlegend": False,
        }})

        # Informational overlay: secondary_metrics (mutator/STW time, or the latency
        # chart's p90/p99/p99.9/p99.99), plotted plain (no regression coloring, no big
        # number, no moving average/std-dev band) alongside the primary series on the
        # same row. Indexed to the primary series' own baseline (not each metric's own
        # min) so the overlay reads as a proportion of it: sec_y_norm[i] ==
        # (sec_raw[i] / primary_raw[i]) * y[i], i.e. this metric's share of the primary
        # metric at that point, times the primary metric's own normalized Y - which
        # simplifies to sec_raw[i] / y_baseline since y[i] itself is primary_raw[i] /
        # y_baseline. The hover label shows that share as a percentage (see
        # sec_pct_text below), not the plotted Y value itself. Drawn on top of (but
        # thinner/more transparent than) the primary series' own line, so it stays
        # visible without competing with it - what this chart is actually for noticing
        # regressions in.
        #
        # When secondary_clamp (mutator/STW, always <= total): clamped to *this row's
        # own* primary-metric range, and not added to the shared y_range_upper/lower -
        # being informational-only, they should never stretch every row's shared axis
        # (which would squash the primary series' own line flat) or bleed into a
        # neighboring benchmark's row. When not (latency's p90+, routinely many times
        # p50): left unclamped, and their own range does extend the shared axis -
        # otherwise they'd be squashed flat against the top of p50's own narrow range,
        # defeating the point of plotting them at all.
        epoch_start = attributes[current_epoch]['start']
        epoch_end = attributes[current_epoch]['end']
        sec_clamp_lower = this_y_lower - Y_RANGE_EXTRA
        sec_clamp_upper = this_y_upper + Y_RANGE_EXTRA
        for sec_key, sec_label, sec_color in secondary_metrics:
            sec_y, _ = history_per_run(runs, plan, bm, sec_key)
            sec_nonzero_in_epoch = [v for v in sec_y[epoch_start:epoch_end + 1] if v != 0]
            if len(sec_nonzero_in_epoch) == 0:
                # No data for this metric on this benchmark (e.g. canary/JikesRVM
                # plans have no MMTk stats at all) - just skip the overlay line.
                continue
            sec_y_norm = normalize_to(sec_y, y_baseline)
            if secondary_clamp:
                sec_y_norm = [min(max(v, sec_clamp_lower), sec_clamp_upper) if v != 0 else 0 for v in sec_y_norm]
            else:
                sec_nonzero_norm = [v for v in sec_y_norm if v != 0]
                if sec_nonzero_norm:
                    if max(sec_nonzero_norm) > y_range_upper:
                        y_range_upper = max(sec_nonzero_norm)
                    if min(sec_nonzero_norm) < y_range_lower:
                        y_range_lower = min(sec_nonzero_norm)

            # Hover label: this metric's own absolute value (with unit) - plus, when
            # secondary_show_percentage (the time chart: mutator + STW make up total
            # time), its share of the primary metric at that point as a percentage.
            # Not the plotted (normalized, possibly clamped) Y value, which isn't
            # meaningful to read as a number on its own.
            sec_hovertext = []
            for sec_v, total_norm_v in zip(sec_y, y):
                if sec_v == 0:
                    sec_hovertext.append("%s: no data" % sec_label)
                    continue
                line = "%s: %s %s" % (sec_label, get_value_text(sec_v), unit)
                if secondary_show_percentage:
                    total_raw_v = total_norm_v * y_baseline
                    line += " (%s of %s)" % ("n/a" if total_raw_v == 0 else "%.1f%%" % (sec_v / total_raw_v * 100), primary_label)
                sec_hovertext.append(line)

            traces.append({
                "name": sec_label,
                "legendgroup": sec_label,
                "showlegend": not sparkline and not secondary_legend_shown[sec_key],
                "hoverinfo": "text",
                "opacity": 0.65,
                "mode": "lines",
                "line": {"width": 1, "color": sec_color},
                "type": "scatter",
                "x": x,
                "y": make_zero_as_none(sec_y_norm),
                "text": sec_hovertext,
                "xaxis": x_axis,
                "yaxis": y_axis,
            })
            secondary_legend_shown[sec_key] = True

        # big number - the total-time regression status (green/red/muted), what this
        # dashboard is for noticing at a glance.
        annotations.append({**annotation, **{
            "text": "%.2f" % current,
            "font": {"color": current_color, "size": big_number_font_size},
            "xanchor": "center",
            "yanchor": "middle",
            "bgcolor": SURFACE,
        }})
        # benchmark name
        annotations.append({**annotation, **{
            "text": "<b>%s" % bm,
            "font": {"color": INK_PRIMARY, "size": bm_name_font_size},
            "xanchor": "center",
            "yanchor": "bottom",
            "yshift": bm_name_y_shift,
            "bgcolor": SURFACE,
        }})
        # aboslute number
        if SHOW_ABS_NUMBER:
            annotations.append({**annotation, **{
                "text": "%.2f ms %s" % (y_cur_aboslute, current_symbol),
                "font": {"color": INK_PRIMARY, "size": ABS_NUMBER_FONT_SIZE},
                "xanchor": "center",
                "yanchor": "bottom",
                "yshift": ABS_NUMBER_FONT_Y_SHIFT
            }})

        if PLOT_MOVING_AVERAGE and not sparkline:
            # moving average
            y_moving_average = moving_average(y, 10)
            traces.append({
                "name": bm,
                "hoverinfo": "none",
                # "fill": "tozeroy",
                "mode": TRACE_MODE,
                "line": {"width": 1, "color": INK_SECONDARY},
                "type": "scatter",
                "x": x,
                "y": y_moving_average,
                "text": ["10-p moving avg: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, y_moving_average)],
                "xaxis": x_axis,
                "yaxis": y_axis,
                "showlegend": False,
            })

        if PLOT_STD_DEV and not sparkline:
            # variance (10p moving average of std dev)
            std_dev_moving_average = moving_average(std, 10)
            variance_trace = {
                "name": bm,
                "hoverinfo": "none",
                "mode": "lines",
                "line_color": INK_MUTED,
                "line": {"width": 0},
                "x": x,
                "xaxis": x_axis,
                "yaxis": y_axis,
                "showlegend": False,
            }
            variance_down = list(map(lambda a, b: a - b if a is not None and b is not None else None, y_moving_average, std_dev_moving_average))
            traces.append({**variance_trace, **{
                # a hack: fill everything under this line the same as the background color,
                # i.e. this trace's fill color must always match plot_bgcolor (SURFACE).
                "fill": "tozeroy",
                "line_color": SURFACE,
                "y": variance_down,
                "text": ["moving avg - std dev: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, variance_down)],
            }})
            variance_up = list(map(lambda a, b: a + b if a is not None and b is not None else None, y_moving_average, std_dev_moving_average))
            traces.append({**variance_trace, **{
                # fill things in muted ink (tinted) between this trace and the trace above
                "fill": "tonexty",
                "fillcolor": "rgba(137, 135, 129, 0.18)",
                "y": variance_up,
                "text": ["moving avg + std dev: %s: %s" % (x, "{:.2f}".format(y) if y is not None else "na") for (x, y) in zip(x_labels, variance_up)],
            }})

        # Mark epoch - draw this after stddev. So it will be rendered on top of stddev
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
            epoch_color = get_regression_color(regress)

            text = "Epoch: %s<br />  start: %.2f ± %.2f, end: %.2f ± %.2f<br />  min: %.2f, max: %.2f" % (v['note'], epoch_normalized_start_y, epoch_normalized_start_y_std, epoch_normalized_end_y, epoch_normalized_end_y_std, epoch_normalized_min_y, epoch_normalized_max_y)

            if not sparkline:
                epoch_vlines.append({**history_trace, **{
                    "hoverinfo": "text",
                    "mode": "lines",
                    "line": { "width": 1, "color": epoch_color },
                    "opacity": 0.2 if epoch_color == STATUS_NEUTRAL else 1,
                    "x": [v['start_x'], v['start_x']],
                    "y": [y_min, y_max],
                    "text": text
                }})

            if epoch_name == current_epoch and not sparkline:
                # Epoch min
                traces.append({**history_trace, **{
                    "hoverinfo": "text",
                    "mode": "markers",
                    "textposition": "top center",
                    "y": keep_first_in_index_range(y, lambda y: y == epoch_normalized_min_y, v['start'], v['end'] + 1),
                    "text": ["best: %s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
                    "textfont_color": STATUS_GOOD,
                    "cliponaxis": False,
                    "marker": { "size": MIN_MAX_MARKER_SIZE, "color": STATUS_GOOD, "symbol": "triangle-down" },
                    "showlegend": False,
                }})
                # Epoch max
                traces.append({**history_trace, **{
                    "hoverinfo": "text",
                    "mode": "markers",
                    "textposition": "top center",
                    "y": keep_first_in_index_range(y, lambda y: y == epoch_normalized_max_y, v['start'], v['end'] + 1),
                    "text": ["worst: %s: %.2f" % (x, y) if y != 0 else "" for (x, y) in zip(x_labels, y)],
                    "textfont_color": STATUS_CRITICAL,
                    "cliponaxis": False,
                    "marker": { "size": MIN_MAX_MARKER_SIZE, "color": STATUS_CRITICAL, "symbol": "triangle-up" },
                    "showlegend": False,
                }})

        # baseline - we will draw one horizontal line per each baseline
        baseline_opacity = 0.6
        baseline_color = BASELINE_COLOR
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

                    if not sparkline:
                        traces.append({**baseline_trace, **{
                            "y": [hline] * len(x),
                            "text": "%s: %.2f" % (build, hline),
                        }})
                    # annotations.append({**baseline_label, **{
                    #     "y": hline,
                    #     "text": "%s: %.2f" % (build, hline),
                    # }})

        row += 1

    # fix range for all the traces
    if SAME_Y_RANGE_IN_ALL_TRACES:
        # epoch_vlines are trace data (a vertical line's y-span), always in normal/
        # linear units regardless of axis type - only the axis "range" itself needs
        # log10 units when log_y (see the per-row comment above).
        if log_y:
            y_range_data = [y_range_lower / 1.3, y_range_upper * 1.3]
            y_range_axis = [math.log10(y_range_data[0]), math.log10(y_range_data[1])]
        else:
            y_range_data = [y_range_lower - Y_RANGE_EXTRA, y_range_upper + Y_RANGE_EXTRA]
            y_range_axis = y_range_data
        for i in range(1, row):
            layout["yaxis%d" % i]["range"] = y_range_axis
        for line in epoch_vlines:
            line["y"] = y_range_data

    fig = Figure(data = Data(traces), layout = layout)
    for anno in annotations:
        fig.add_annotation(anno)
    for line in baseline_hlines:
        fig.add_shape(line)
    for vline in epoch_vlines:
        fig.add_trace(vline)

    fig.update_layout(hovermode='x')
    fig.update_layout(hoverdistance=1)
    fig.update_layout(margin=SPARKLINE_MARGIN if sparkline else FULL_MARGIN)

    return fig


# Secondary metrics for the latency chart (see plot_history's secondary_metrics
# param) - p50/p90/p99/p99.9, plotted alongside latency.p9999 (the primary series -
# the tail percentile people actually watch for SLA regressions) exactly like the
# time chart plots mutator/STW alongside time.total. Each gets its own gray shade
# (darkest for p50, lightest for p99.9) since, unlike mutator/STW, there is more
# than one of them on the same row.
LATENCY_SECONDARY_METRICS = [
    ("latency.p50", "p50", "#5c5a54"),
    ("latency.p90", "p90", "#7b7972"),
    ("latency.p99", "p99", "#9a978e"),
    ("latency.p999", "p99.9", "#b9b6ac"),
]


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
        attrs[epoch_name]['start_x'] = x[idx]
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

    # Decide the color for each segment, based on the best value up to that point in the epoch
    for name, epoch in attrs.items():
        start = epoch['start']
        end = epoch['end']

        # The best result in this epoch so far
        best = -1

        line_colors = []
        line_colors_info = []

        for i in range(start, end + 1):
            if y[i] == 0:
                # No data
                line_colors.append(STATUS_NEUTRAL)
                line_colors_info.append(None)
                continue

            if best == -1:
                best = i

            trend = check_regression(y[best], y_std[best], y[i], y_std[i])
            if trend == "improvement":
                best = i
            line_colors.append(get_regression_color(trend))
            line_colors_info.append({ "label": x_labels[best], "value": y[best], "regression": trend })
        epoch['line_colors'] = line_colors
        epoch['line_colors_info'] = line_colors_info

    return attrs

# Return improvement, or regression, or neutral
def check_regression(r1, std1, r2, std2):
    def z_score_regression(r1, std1, r2, std2):
        import math
        pooled_std = math.sqrt(std1**2 + std2**2)
        z_score = (r2 - r1) / pooled_std

        # A z-score less than -1.96 indicates a statistically significant regression at 95% confidence
        if z_score < -1.96:
            return "regression"
        # A z-score greater than 1.96 indicates a statistically significant improvement
        elif z_score > 1.96:
            return "improvement"
        else:
            return "neutral"

    def boundary_regression(r1, std1, r2, std2):
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

    # Use boundary regression. It is less statistically sound, but more intuitive for people to check the result.
    return boundary_regression(r1, std1, r2, std2)


def get_regression_color(regression):
    match regression:
        case "regression": return STATUS_CRITICAL
        case "improvement": return STATUS_GOOD
        case "neutral": return STATUS_NEUTRAL
        case _: raise Exception('Unexpected regression string:' + regression)


def get_regression_symbol(regression):
    match regression:
        case "regression": return "△"
        case "improvement": return "▽"
        case "neutral": return "~"
        case _: raise Exception('Unexpected regression string:' + regression)


def get_value_text(value):
    if value is None:
        return "none"
    else:
        return "%.2f" % value


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
