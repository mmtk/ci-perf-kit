""" Compares two builds (e.g. trunk vs a PR branch) that were run together in
    one running-ng invocation (see running-openjdk-*-compare.yml), producing:
      - <output_dir>/report.md: a "Time" Markdown table (one column per
        Total/Mutator/STW) and, only for plans opted into `latency: true` in
        <plot_config> (see configs/openjdk-plot.yml), a "Tail latency" table
        (one column per p50/p90/p99/p99.9/p99.99) - one row per benchmark
        plus trailing min/max/mean/geomean summary rows, each cell branch
        normalized to trunk as a percentage difference with a 95%
        confidence interval.
      - <output_dir>/plots/<plan>_time.png: the same Time grouping as a
        chart - 3 bars per benchmark.
      - <output_dir>/plots/<plan>_latency.png: the same Tail latency
        grouping as a chart - 5 bars per benchmark.
      - <output_dir>/plots/<plan>_<metric>.png: one chart per any other
        metric the logs happen to contain (an MMTk stat outside the two
        groups above) - a single bar per benchmark.
    Every bar is build2 (branch)'s value normalized to build1 (trunk)'s mean
    for that benchmark - trunk itself isn't plotted, since normalized to
    itself it's always ~1.0 and adds nothing. Bars have 95%
    confidence-interval error bars, and each chart has trailing
    min/max/mean/geomean summary bars (one per metric in the chart).

    Usage: python compare_plot.py <log_dir> <plan> <build1> <build2> <invocations> <output_dir> <plot_config>
    build1 is the normalization baseline (trunk); build2 (branch) is plotted
    relative to it. <plot_config> is a configs/*-plot.yml path (e.g.
    configs/openjdk-plot.yml) - only used to look up whether <plan> is
    latency-enabled.
"""

import sys
import os
import numpy as np
from scipy import stats
from scipy.stats import gmean

import parse
import plot as plotmod

if len(sys.argv) != 8:
    print("Usage: python compare_plot.py <log_dir> <plan> <build1> <build2> <invocations> <output_dir> <plot_config>")
    sys.exit(1)

log_dir = sys.argv[1]
plan = sys.argv[2]
build1 = sys.argv[3]
build2 = sys.argv[4]
invocations = int(sys.argv[5])
output_dir = sys.argv[6]
plot_config_path = sys.argv[7]

run_id, results, commit_info = parse.parse_run(log_dir, invocations)
results = [r for r in results if r is not None]

benchmarks = sorted(set(r['benchmark'] for r in results))

RESERVED_KEYS = {'log_name', 'benchmark', 'build', 'status', 'succeeded_runs'}
LATENCY_PREFIX = 'latency.'

plot_config = parse.parse_yaml(plot_config_path)
plan_config = parse.get_config_for_plan(plot_config, plan)
LATENCY_ENABLED = bool(plan_config) and plan_config.get('latency', False)
if not LATENCY_ENABLED:
    print("Plan %s is not configured for latency (see %s) - skipping latency metrics." % (plan, plot_config_path))

CONFIDENCE = 0.95

# The only metrics we plot/tabulate: the 3 time metrics merged into a single
# chart/table (3 bars/columns per benchmark), and, for latency-enabled plans,
# the 5 latency percentiles likewise merged into one chart/table. Colors
# reused from plot.py's own SECONDARY_METRICS/LATENCY_SECONDARY_METRICS so
# this reads as part of the same palette family as the history reports.
TIME_METRICS = [
    ('time.total', 'Total', plotmod.INK_PRIMARY),
    ('time.other', 'Mutator', "#2a78d6"),
    ('time.stw', 'STW', "#4a3aa7"),
]
LATENCY_METRICS = [
    ('latency.p50', 'p50', "#b9b6ac"),
    ('latency.p90', 'p90', "#9a978e"),
    ('latency.p99', 'p99', "#7b7972"),
    ('latency.p999', 'p99.9', "#5c5a54"),
    ('latency.p9999', 'p99.99', plotmod.BASELINE_COLOR),
]


def discovered_metric_keys():
    """ Every list-valued metric key present across any parsed result (union,
        since not every benchmark/build necessarily has the same set of MMTk
        stat keys) - used to check which of TIME_METRICS/LATENCY_METRICS
        actually have data. Latency percentiles are only included if the
        plan is latency-enabled (see LATENCY_ENABLED above) - like
        history_report.py, we don't plot them for plans nobody asked to
        track latency for, even though the underlying benchmarks
        (cassandra/h2/lusearch/tomcat) print tail latency regardless of
        which plan is running. """
    keys = set()
    for r in results:
        for k, v in r.items():
            if k in RESERVED_KEYS:
                continue
            if k.startswith(LATENCY_PREFIX) and not LATENCY_ENABLED:
                continue
            if isinstance(v, list):
                keys.add(k)
    return keys


def get_result(build, benchmark):
    matches = [r for r in results if r['benchmark'] == benchmark and r['build'] == build]
    return matches[0] if matches else None


def mean_ci(arr, confidence=CONFIDENCE):
    """ Mean and 95% t-distribution confidence-interval half-width - same
        formula the old compare_report.py used. """
    arr = np.asarray(arr, dtype=float)
    mean = np.mean(arr)
    if len(arr) > 1:
        ci = stats.sem(arr) * stats.t.ppf((1 + confidence) / 2., len(arr) - 1)
    else:
        ci = 0.0
    return mean, ci


# ---------------------------------------------------------------------------
# report.md: one Markdown table per metric group (Time, Tail latency) - one
# column per metric in the group, one row per benchmark. Uses the same
# compute_branch_ratios as the plots (see below), so the tables and the
# charts always agree.
# ---------------------------------------------------------------------------

def format_pct_ci(mean, ci):
    return '%+.2f%% ±%.2f%%' % ((mean - 1) * 100, ci * 100)


def build_metric_table(metrics):
    """ metrics: list of (metric_key, label, color) tuples, e.g. TIME_METRICS.
        Returns a Markdown table with one column per metric that actually
        has data, or None if none of them do. """
    ratios_by_metric = {}
    for key, _, _ in metrics:
        ratios = compute_branch_ratios(key)
        if len(ratios) > 0:
            ratios_by_metric[key] = ratios

    if len(ratios_by_metric) == 0:
        return None

    present_metrics = [(key, label) for key, label, _ in metrics if key in ratios_by_metric]
    ordered_benchmarks = [bm for bm in benchmarks if any(bm in r for r in ratios_by_metric.values())]

    lines = []
    lines.append('|Benchmark|' + '|'.join(label for _, label in present_metrics) + '|')
    lines.append('|:-------:|' + '|'.join([':-------------------:'] * len(present_metrics)) + '|')

    for bm in ordered_benchmarks:
        cells = []
        for key, _ in present_metrics:
            ratios = ratios_by_metric[key]
            cells.append(format_pct_ci(*ratios[bm]) if bm in ratios else ':x:')
        lines.append('|%s|%s|' % (bm, '|'.join(cells)))

    # Trailing min/max/mean/geomean summary rows, matching the summary bars
    # on the corresponding chart - no CI here, same as those bars.
    for summary_label in SUMMARY_LABELS:
        cells = []
        for key, _ in present_metrics:
            summary_mean = summary_stats(ratios_by_metric[key])[summary_label]
            cells.append('%+.2f%%' % ((summary_mean - 1) * 100))
        lines.append('|**%s**|%s|' % (summary_label, '|'.join(cells)))

    return '\n'.join(lines)


def build_report():
    lines = []
    lines.append('%s (%s)' % (plan, run_id))
    lines.append('')

    time_table = build_metric_table(TIME_METRICS)
    if time_table:
        lines.append('### Time')
        lines.append('')
        lines.append(time_table)
        lines.append('')

    if LATENCY_ENABLED:
        latency_table = build_metric_table(LATENCY_METRICS)
        if latency_table:
            lines.append('### Tail latency')
            lines.append('')
            lines.append(latency_table)
            lines.append('')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# plots: one normalized, grouped bar chart per metric group (time, latency,
# or a single other metric on its own) - build2 (branch) only, since build1
# (trunk) normalized to itself is always ~1.0 and isn't worth drawing.
# ---------------------------------------------------------------------------

def compute_branch_ratios(metric_key):
    """ For each benchmark, build2 (branch)'s values normalized to build1
        (trunk)'s mean for that benchmark. Returns an ordered dict of
        benchmark -> (mean_ratio, ci), skipping benchmarks where either
        build has no (or all-zero) data for this metric. """
    per_benchmark = {}
    for bm in benchmarks:
        trunk_result = get_result(build1, bm)
        branch_result = get_result(build2, bm)
        if trunk_result is None or branch_result is None:
            continue
        trunk_vals = trunk_result.get(metric_key, [])
        branch_vals = branch_result.get(metric_key, [])
        if len(trunk_vals) == 0 or len(branch_vals) == 0:
            continue
        trunk_mean_abs = np.mean(trunk_vals)
        # Some MMTk stats use +-inf as a "not applicable to this
        # benchmark/plan" sentinel (e.g. total-work.time.max/min). Treat
        # that the same as a zero baseline - can't normalize to it, and
        # inf/inf or x/inf would otherwise silently produce NaN, which
        # breaks the whole chart's axis range further down.
        if trunk_mean_abs == 0 or not np.isfinite(trunk_mean_abs):
            continue
        ratio_mean, ratio_ci = mean_ci(plotmod.normalize_to(branch_vals, trunk_mean_abs))
        if not np.isfinite(ratio_mean):
            continue
        per_benchmark[bm] = (ratio_mean, ratio_ci)
    return per_benchmark


def summary_stats(per_benchmark_ratios):
    means = [mean for mean, _ in per_benchmark_ratios.values()]
    return {
        'min': min(means),
        'max': max(means),
        'mean': np.mean(means),
        'geomean': gmean(means),
    }


SUMMARY_LABELS = ['min', 'max', 'mean', 'geomean']


def plot_metric_group(metrics, chart_title, filename, plots_dir):
    """ metrics: list of (metric_key, label, color) tuples, e.g. TIME_METRICS.
        One bar trace per metric, sharing an x-axis of benchmark + a blank
        spacer + SUMMARY_LABELS. Metrics with no data at all are dropped;
        returns None (and plots nothing) if none of them have any. """
    import plotly.graph_objs as go

    ratios_by_metric = {}
    for key, _, _ in metrics:
        ratios = compute_branch_ratios(key)
        if len(ratios) == 0:
            print("Skipping %s: no benchmark has data for both builds." % key)
            continue
        ratios_by_metric[key] = ratios

    if len(ratios_by_metric) == 0:
        return None

    ordered_benchmarks = [bm for bm in benchmarks if any(bm in r for r in ratios_by_metric.values())]
    x = ordered_benchmarks + [' '] + SUMMARY_LABELS

    traces = []
    all_points = []
    for key, label, color in metrics:
        if key not in ratios_by_metric:
            continue
        ratios = ratios_by_metric[key]
        summary = summary_stats(ratios)

        y, err = [], []
        for bm in ordered_benchmarks:
            if bm in ratios:
                mean, ci = ratios[bm]
                y.append(mean)
                err.append(ci)
            else:
                y.append(None)
                err.append(0)
        y.append(None)
        err.append(0)
        for summary_label in SUMMARY_LABELS:
            y.append(summary[summary_label])
            err.append(0)

        traces.append(go.Bar(name=label, x=x, y=y, error_y=dict(type='data', array=err, visible=True), marker_color=color))
        all_points.extend((v, e) for v, e in zip(y, err) if v is not None)

    # Bars start at 0, like a normal bar chart - just pad the top a little
    # so the tallest bar/error-bar cap isn't flush against the plot edge.
    y_high = max(v + e for v, e in all_points)
    y_pad = max(y_high * 0.05, 0.02)

    width = max(900, 45 * len(x))
    fig = go.Figure(data=traces)
    fig.update_layout(
        barmode='group',
        width=width,
        height=550,
        font={"family": plotmod.FONT_FAMILY, "color": plotmod.INK_PRIMARY},
        plot_bgcolor=plotmod.SURFACE,
        paper_bgcolor=plotmod.SURFACE,
        title={
            "text": "%s - %s (normalized to %s)" % (plan, chart_title, build1),
            "font": {"size": 16, "color": plotmod.INK_PRIMARY},
        },
        xaxis={"tickangle": -30, "gridcolor": plotmod.GRIDLINE, "linecolor": plotmod.AXIS_LINE},
        yaxis={
            "title": chart_title,
            "gridcolor": plotmod.GRIDLINE,
            "linecolor": plotmod.AXIS_LINE,
            "range": [0, y_high + y_pad],
        },
        legend={"orientation": "h", "y": -0.3},
    )
    fig.add_hline(y=1.0, line_dash="dash", line_color=plotmod.INK_MUTED)

    out_path = os.path.join(plots_dir, filename)
    fig.write_image(out_path, scale=2)
    return filename


def main():
    os.makedirs(output_dir, exist_ok=True)
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'report.md'), 'w') as f:
        f.write(build_report())

    discovered = discovered_metric_keys()

    time_metrics = [m for m in TIME_METRICS if m[0] in discovered]
    if time_metrics:
        plot_metric_group(time_metrics, "Time", "%s_time.png" % plan, plots_dir)

    if LATENCY_ENABLED:
        latency_metrics = [m for m in LATENCY_METRICS if m[0] in discovered]
        if latency_metrics:
            plot_metric_group(latency_metrics, "Tail latency", "%s_latency.png" % plan, plots_dir)


if __name__ == '__main__':
    main()
