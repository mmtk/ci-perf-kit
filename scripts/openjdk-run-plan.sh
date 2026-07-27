set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Run OpenJDK benchmarks for a single plan, then save and commit the result.
# Assumes the runtimes referenced by $config already exist under $kit_build
# (e.g. built by openjdk-build.sh, or - for the canary plan - copied into
# place by the caller as $kit_build/jdk-mmtk-canary).

# plan_name: result dir name under result_repo/openjdk (e.g. nogc, semispace, canary)
plan_name=$1
# config: running-ng config filename under configs/ (e.g. running-openjdk-nogc-complete.yml)
config=$2
# heap_modifier: passed straight to run_benchmarks (0 for NoGC-style fixed heaps)
heap_modifier=$3
# commit_rev: revision id used in the result-repo commit message
commit_rev=$4

invocations=$history_invocations
# Use this when testing the scripts so that tests run faster, albeit producing less accurate results.
if [ "$OPENJDK_HISTORY_RUN_TEST_FAST" = "1" ]; then
    invocations=1
fi

ensure_empty_dir $log_dir
checkout_result_repo

# Run
run_id=$(run_benchmarks $log_dir $kit_root/configs/$config $heap_modifier $invocations)

# Carry the build's commit info (if any) into this run's log folder, so
# history_report.py can show which mmtk-core/mmtk-openjdk commits produced
# this datapoint. Skipped for canary: it runs a fixed, downloaded release
# binary rather than something built from these commits, so attaching them
# would be misleading.
commit_info=$kit_build/jdk-mmtk/commit-info.yml
if [ "$plan_name" != "canary" ] && [ -f "$commit_info" ]; then
    cp $commit_info $log_dir/$run_id/commit-info.yml
fi

# Save result
RESULT_DIR=$result_repo_dir/openjdk/$plan_name
mkdir -p $RESULT_DIR
cp -r $log_dir/$run_id $RESULT_DIR

# Commit result
commit_result_repo 'OpenJDK Binding: '$commit_rev
