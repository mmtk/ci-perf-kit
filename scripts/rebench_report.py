# Only execute this under microbm directory

import subprocess
import sys
import re

output = ''
def append_output(msg):
    global output
    output += msg + '\n'

args = sys.argv[1:]

print("Running: %s" % args)
try:
    rebench_run = subprocess.check_output(args)
    
    # print(rebench_run)
    extract = rebench_run.split('--------------------------------------------------------------------------------------------------------------')
    table = extract[-2]
    results_by_bm = {}
    for row in table.split('\n'):
        cols = row.split()
        if len(cols) == 0:
            continue
        
        bm = cols[0]
        build = cols[1]
        mean = cols[-1]
        
        item = {}
        item['benchmark'] = bm
        item['suite'] = cols[2]
        item['mean'] = { build: mean }

        if bm in results_by_bm:
            results_by_bm[bm]['mean'][build] = mean
        else:
            results_by_bm[bm] = item
    
    print(results_by_bm)
    append_output('|Benchmark|Trunk (ms)|Branch (ms)|Diff|')
    append_output('|:-------:|:--------:|:---------:|:---:|')

    bms = results_by_bm.keys()
    bms.sort()
    for bm in bms:
        item = results_by_bm[bm]
        for build, val in item['mean'].iteritems():
            if 'trunk' in build.lower():
                trunk = float(val)
            else:
                branch = float(val)
        
        diff = (branch - trunk) / trunk
        diff_text = '%+.2f%%' % (diff * 100)
        if diff >= 0.01:
            diff_text += ' :red_square:'
        elif diff <= -0.01:
            diff_text += ' :green_square:'
        append_output('|%s|%s|%s|%s|' % (bm, trunk, branch, diff_text))
    
    print(output)


except subprocess.CalledProcessError as e:
    print("CallProcessError: %s" % e)
    print("output: ")
    print(e.output)