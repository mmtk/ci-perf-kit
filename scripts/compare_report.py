import parse
import sys
import os

output = ''
def append_output(msg):
    global output
    output += msg + '\n'

# log folder
if len(sys.argv) != 6:
    print("Usage: python compare_report.py <log_dir> <plan> <build1> <build2> <invocations>")
    sys.exit(1)

folder = sys.argv[1]
plan = sys.argv[2]
build1 = sys.argv[3]
build2 = sys.argv[4]
expected_invocations = int(sys.argv[5])
run_id = os.path.basename(os.path.normpath(folder))

# list all the logs
logs = parse.list_logs(folder)

results = []
for l in logs:
    results.append(parse.parse_log(os.path.join(folder, l), expected_invocations))

# benchmarks
benchmarks = [r['benchmark'] for r in results]
benchmarks = list(set(benchmarks))
benchmarks.sort()

append_output('%s (%s)' % (plan, run_id))
append_output('-----')
append_output('|Benchmark| Trunk(ms)  |                       |        | Branch(ms)  |                       |        | Diff |                       |')
append_output('|:-------:|:----------:|:---------------------:|:------:|:-----------:|:---------------------:|:------:|:----:|:---------------------:|')
append_output('|         | mean       | mean without outliers | median | mean        | mean without outliers | median | mean | mean without outliers |')

# for each benchmark
for bm in benchmarks:
    def average_execution_time(r):
        if len(r['execution_times']) == 0:
            return None
        else:
            return sum(r['execution_times']) / len(r['execution_times'])
    
    def get_result(build):
        result = None
        
        has_result = [r for r in results if r['benchmark'] == bm and r['build'] == build][:1]
        if len(has_result) != 0:
            result = has_result[0]

        return result
    
    def get_statistics(result):
        ret = {}

        import numpy as np
        from scipy import stats
        arr = np.array(result['execution_times'])

        confidence = 0.95

        # mean
        ret['mean'] = np.mean(arr)
        # confidence interval
        ret['mean_ci'] = stats.sem(arr) * stats.t.ppf((1 + confidence) / 2., len(arr) - 1)
        # and median
        ret['median'] = np.median(arr)

        # outliers
        z_score = stats.zscore(arr)
        # only keep data whose zscore is within 3
        filtered = [r for r, z in zip(arr, z_score) if z < 3]
        # number of outliers and mean without outliers
        ret['n_outliers'] = len(arr) - len(filtered)
        ret['mean_without_outliers'] = np.mean(filtered)
        ret['mean_without_outliers_ci'] = stats.sem(filtered) * stats.t.ppf((1 + confidence) / 2., len(filtered) - 1)

        return ret

    trunk_result = get_result(build1)
    branch_result = get_result(build2)

    def format_build_statistics(result):
        s = get_statistics(result)
        
        text_mean = None

        if result['status'] == 'success':
            text_mean = '%.2f ±%.2f' % (s['mean'], s['mean_ci'])
        elif result['status'] == 'partial_fail':
            text_mean = '%.2f ±%.2f :warning: %d/%d failed' % (s['mean'], s['mean_ci'], expected_invocations - result['succeeded_runs'], expected_invocations)
        elif result['status'] == 'fail':
            text_mean = ':x:'
        
        text_mean_without_outliers = None            
        if result['status'] == 'fail':
            text_mean_without_outliers = ':x:'
        else:
            if s['n_outliers'] != 0:
                text_mean_without_outliers = '%.2f ±%.2f :warning: %d removed' % (s['mean_without_outliers'], s['mean_without_outliers_ci'], s['n_outliers'])
            else:
                text_mean_without_outliers = '%.2f ±%.2f' % (s['mean_without_outliers'], s['mean_without_outliers_ci'])
        
        text_median = None
        if result['status'] != 'fail':
            text_median = s['median']
        else:
            text_median = ':x:'
        
        return text_mean, text_mean_without_outliers, text_median, s
    
    def format_diff(stats1, stats2, key, should_highlight):
        # mean diff
        diff = 0
        if stats1[key] is not None and stats2[key] is not None:
            diff = (stats2[key] - stats1[key]) / stats1[key]
        diff_text = '%+.2f%%' % (diff * 100)

        if should_highlight:
            if diff >= 0.01:
                diff_text += ' :red_square:'
            elif diff <= -0.01:
                diff_text += ' :green_square:'
        return diff_text
    
    trunk_mean, trunk_mean_without_outliers, trunk_median, trunk_stats = format_build_statistics(trunk_result)
    branch_mean, branch_mean_without_outliers, branch_median, branch_stats = format_build_statistics(branch_result)

    mean_diff = format_diff(trunk_stats, branch_stats, 'mean', False)
    mean_without_outliers_diff = format_diff(trunk_stats, branch_stats, 'mean_without_outliers', True)
    
    append_output('|%s|%s|%s|%s|%s|%s|%s|%s|%s|' % (bm, trunk_mean, trunk_mean_without_outliers, trunk_median, branch_mean, branch_mean_without_outliers, branch_median, mean_diff, mean_without_outliers_diff))

append_output('')
print(output)
