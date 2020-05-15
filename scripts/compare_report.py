import parse
import sys
import os

output = ''
def append_output(msg):
    global output
    output += msg

# log folder
if len(sys.argv) != 4:
    print "Usage: python compare_report.py <plan> <log_dir> <invocations>"
    sys.exit(1)

plan = sys.argv[1]
folder = sys.argv[2]
expected_invocations = int(sys.argv[3])
trunk_build = plan + '_Trunk'
branch_build = plan + '_Branch'

# list all the logs
logs = os.listdir(folder)

results = []
for l in logs:
    results.append(parse.parse_log(os.path.join(folder, l), expected_invocations))

# benchmarks
benchmarks = [r['benchmark'] for r in results]
benchmarks = list(set(benchmarks))
benchmarks.sort()

append_output('%s' % plan)
append_output('=====')
append_output('|Benchmark| %s  | %s  |Diff |' % (trunk_build, branch_build))
append_output('|:-------:|:---:|:---:|:---:|')

# for each benchmark
for bm in benchmarks:
    def average_execution_time(r):
        if len(r['execution_times']) == 0:
            return None
        else:
            return sum(r['execution_times']) / len(r['execution_times'])
    
    def format_result(build):
        time = None
        text = ':x:'
        has_result = [r for r in results if r['benchmark'] == bm and r['build'] == build][:1]
        if len(has_result) != 0:
            result = has_result[0]
            time = average_execution_time(result)
            if result['status'] == 'partial_fail':
                text = '%s :warning:' % time
            elif result['status'] == 'fail':
                text = ':x:'
            elif result['status'] == 'success':
                text = time
        return time, text

    # trunk
    trunk_time, trunk_text = format_result(trunk_build)
    
    # branch
    branch_time, branch_text = format_result(branch_build)
    
    diff = 0
    if trunk_time is not None and branch_time is not None:
        diff = (branch_time - trunk_time) / trunk_time
    
    append_output('|%s|%s|%s|%+.2f%%|' % (bm, trunk_text, branch_text, diff*100))

append_output('\n')