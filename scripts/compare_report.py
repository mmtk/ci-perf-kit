import parse
import sys
import os

EXPECTED_INVOCATIONS = 5

output = ''
def append_output(msg):
    print(msg)
    global output
    output += msg

# log folder
if len(sys.argv) != 3:
    print "Usage: python compare_report.py plan log_dir"
    sys.exit(1)

plan = sys.argv[1]
folder = sys.argv[2]
trunk_build = plan + '_Trunk'
branch_build = plan + '_Branch'

# list all the logs
logs = os.listdir(folder)

results = []
for l in logs:
    results.append(parse.parse_log(os.path.join(folder, l), EXPECTED_INVOCATIONS))

# benchmarks
benchmarks = [r['benchmark'] for r in results]
benchmarks = list(set(benchmarks))
benchmarks.sort()

append_output('|Benchmark| %s  | %s  |Diff |' % (trunk_build, branch_build))
append_output('|:-------:|:---:|:---:|:---:|')

# for each benchmark
for bm in benchmarks:
    def average_execution_time(r):
        if len(r['execution_times']) == 0:
            return None
        else:
            return sum(r['execution_times']) / len(r['execution_times'])

    # trunk
    trunk_time = None
    has_trunk_result = [r for r in results if r['benchmark'] == bm and r['build'] == trunk_build][:1]
    if len(has_trunk_result) != 0:
        trunk_result = has_trunk_result[0]
        trunk_time = average_execution_time(trunk_result)
    
    # branch
    branch_time = None
    has_branch_result = [r for r in results if r['benchmark'] == bm and r['build'] == branch_build][:1]
    if len(has_branch_result) != 0:
        branch_result = has_branch_result[0]
        branch_time = average_execution_time(branch_result)
    
    diff = 0
    if trunk_time is not None and branch_time is not None:
        diff = (branch_time - trunk_time) / trunk_time
    
    append_output('|%s|%s|%s|%+.4f|' % (bm, trunk_time, branch_time, diff))