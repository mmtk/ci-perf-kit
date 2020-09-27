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
    
    # ReBench prints variable-lengthed separator lines. We hope this string below is enough to capture it. 
    extract = rebench_run.split(b'------------------------------------------------------------------------')
    table = extract[-2]
    table = table.strip(b'-').rstrip(b'-') # We strip extra dashes.
    results_by_bm = {}
    for row in table.split(b'\n'):
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
    
    append_output('|Benchmark|Trunk (ms)|Branch (ms)|Diff|')
    append_output('|:-------:|:--------:|:---------:|:---:|')

    bms = list(results_by_bm.keys())
    bms.sort()
    for bm in bms:
        item = results_by_bm[bm]
        for build, val in item['mean'].items():
            if b'trunk' in build.lower():
                trunk = float(val)
            else:
                branch = float(val)
        
        diff = (branch - trunk) / trunk
        diff_text = '%+.2f%%' % (diff * 100)
        if diff >= 0.01:
            diff_text += ' :red_square:'
        elif diff <= -0.01:
            diff_text += ' :green_square:'
        append_output('|%s|%.2f|%.2f|%s|' % (str(bm, "utf-8"), trunk / 1000000, branch / 1000000, diff_text))
    
    print(output)


except subprocess.CalledProcessError as e:
    print("CallProcessError: %s" % e)
    print("output: ")
    print(e.output)