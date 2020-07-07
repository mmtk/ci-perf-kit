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
logs = os.listdir(folder)

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
        # time = None
        # text = ':x:'
        result = None
        
        has_result = [r for r in results if r['benchmark'] == bm and r['build'] == build][:1]
        if len(has_result) != 0:
            result = has_result[0]

            # # remove outliers
            # import numpy as np
            # from scipy import stats
            # arr = np.array(result['execution_times'])
            # z_score = stats.zscore(arr)

            # # only keep data whose zscore is within 3
            # result['execution_times'] = [r for r, z in zip(arr, z_score) if z < 3]

            # time = average_execution_time(result)
            # if result['status'] == 'partial_fail':
            #     text = '%s :warning:%d/%d failed' % (time, expected_invocations - result['succeeded_runs'], expected_invocations)
            # elif result['status'] == 'fail':
            #     text = ':x:'
            # elif result['status'] == 'success':
            #     text = time
        return result
    
    def get_statistics(result):
        ret = {}

        import numpy as np
        from scipy import stats
        arr = np.array(result['execution_times'])

        # mean and median
        ret['mean'] = np.mean(arr)
        ret['median'] = np.median(arr)

        # outliers
        z_score = stats.zscore(arr)
        # only keep data whose zscore is within 3
        filtered = [r for r, z in zip(arr, z_score) if z < 3]
        # number of outliers and mean without outliers
        ret['n_outliers'] = len(arr) - len(filtered)
        ret['mean_without_outliers'] = np.mean(filtered)

        return ret

    trunk_result = get_result(build1)
    branch_result = get_result(build2)

    def format_build_statistics(result):
        s = get_statistics(result)
        
        text_mean = None

        if result['status'] == 'success':
            text_mean = '%.2f' % s['mean']
        elif result['status'] == 'partial_fail':
            text_mean = '%.2f :warning: %d/%d failed' % (s['mean'], expected_invocations - result['succeeded_runs'], expected_invocations)
        elif result['status'] == 'fail':
            text_mean = ':x:'
        
        text_mean_without_outliers = None            
        if result['status'] == 'fail':
            text_mean_without_outliers = ':x:'
        else:
            if s['n_outliers'] != 0:
                text_mean_without_outliers = '%.2f :warning: %d removed' % (s['mean_without_outliers'], s['n_outliers'])
            else:
                text_mean_without_outliers = '%.2f' % s['mean_without_outliers']
        
        text_median = None
        if result['status'] != 'fail':
            text_median = s['median']
        else:
            text_median = ':x:'
        
        return text_mean, text_mean_without_outliers, text_median, s

        
        # trunk_arr = np.array(trunk_result['execution_times'])
        # branch_arr = np.array(branch_result['execution_times'])

        # # mean
        # trunk_mean = np.mean(trunk_arr)
        # trunk_median = np.median(trunk_arr)

        # # statistical significance
        # x = np.array(trunk_result['execution_times'])
        # y = np.array(branch_result['execution_times'])

        # t, p = stats.ttest_ind(x, y)
        # critical_value = stats.t.ppf(0.95, len(x) + len(y))
        
        # print(bm)
        # print(x)
        # print("avg = %f, 25p = %f, 50p = %f, 75p = %f" % (trunk_time, np.percentile(x, 25), np.percentile(x, 50), np.percentile(x, 75)))
        # print("median = %f" % np.median(x))
        # print(y)
        # print("avg = %f, 25p = %f, 50p = %f, 75p = %f" % (branch_time, np.percentile(y, 25), np.percentile(y, 50), np.percentile(y, 75)))
        # print("median = %f" % np.median(y))
        # print("t=%f, p=%f, critical=%f" % (t, p, critical_value))
        # print("significant change: %s" % (p < 0.05))
        # print("significant increase: %s" % (p / 2 < 0.05 and t > 0))
        # print("significant decrease: %s" % (p / 2 < 0.05 and t < 0))

        # s_x_2 = x.var(ddof=1)
        # s_y_2 = y.var(ddof=1)

        # t = (x.mean() - y.mean()) / sqrt(s_x_2 / len(x) + s_y_2 / len(y))

        # # degree of freedom
        # df = len(x) + len(y) - 2
        # # p-value
        # p = 1 - stats.t.cdf(t, df = df)
    
    def format_diff(stats1, stats2):
        # mean diff
        diff = 0
        if stats1['mean'] is not None and stats2['mean'] is not None:
            diff = (stats1['mean'] - stats2['mean']) / stats1['mean']
        diff_text = '%+.2f%%' % (diff * 100)
        
        # mean without outliers diff
        diff2 = 0
        if stats1['mean_without_outliers'] is not None and stats2['mean_without_outliers'] is not None:
            diff = (stats1['mean_without_outliers'] - stats2['mean_without_outliers']) / stats1['mean_without_outliers']
        diff2_text = '%+.2f%%' % (diff * 100)
        # use different color emoji for better/worse result
        if diff >= 0.01:
            diff_text += ' :red_square:'
        elif diff <= -0.01:
            diff_text += ' :green_square:'
        
        return diff_text, diff2_text
    
    trunk_mean, trunk_mean_without_outliers, trunk_median, trunk_stats = format_build_statistics(trunk_result)
    branch_mean, branch_mean_without_outliers, branch_median, branch_stats = format_build_statistics(branch_result)

    diff_text, diff2_text = format_diff(trunk_stats, branch_stats)
    
    append_output('|%s|%s|%s|%s|%s|%s|%s|%s|%s|' % (bm, trunk_mean, trunk_mean_without_outliers, trunk_median, branch_mean, branch_mean_without_outliers, branch_median, diff_text, diff2_text))

append_output('')
print(output)
