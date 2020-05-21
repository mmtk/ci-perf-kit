import re
import os

# Given a log file and expected invocations, return the result
def parse_log(log_file, n_invocations = None):
    # return a dict of the parse result
    ret = {}

    ret['log_name'] = os.path.basename(log_file)

    # log_name is something like 'antlr.40000.2000.Trunk.ig.log.gz'
    file_name_matcher = re.match("(.*)\.\d+\.\d+\.([^\.]*)(\..*)?\.log\.gz", ret['log_name'])
    if file_name_matcher:
        ret['benchmark'] = file_name_matcher.group(1)
        ret['build'] = file_name_matcher.group(2)
    else:
        print("Unexpected log file name: %s" % ret['log_name'])
        return None

    # read execution time
    import gzip
    with gzip.open(log_file, 'r') as f:
        content = f.read()
        lines = content.splitlines()
        execution_times = []
        for line in lines:
            line = str(line)
            if len(line) == 0:
                continue
            
            matcher = re.match(".*PASSED in (\d+) msec.*", line)
            if matcher:
                execution_times.append(float(matcher.group(1)))
        ret['execution_times'] = execution_times

    # if no n_invocations is passed in, we do not check how many results we have
    if n_invocations == None:
        return ret

    # otherwise check status
    n_results = len(ret['execution_times'])
    if n_results == 0:
        ret['status'] = 'fail'
    elif n_results == n_invocations:
        ret['status'] = 'success'
    elif n_results < n_invocations:
        ret['status'] = 'partial_fail'
    else:
        ret['status'] = 'unexpected_invocation_number'

    return ret

# Given a log folder, return the result
def parse_run(log_folder, n_invocations = None):
    run_id = os.path.basename(os.path.normpath(log_folder))

    results = []
    logs = os.listdir(log_folder)
    for l in logs:
        results.append(parse_log(os.path.join(log_folder, l), n_invocations))
    return run_id, results
