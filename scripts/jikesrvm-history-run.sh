set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_binding=$(realpath $1)
output_dir=$(realpath -m $2)
jikesrvm_rev=$(git -C $jikesrvm_binding rev-parse HEAD)

# JikesRVM root
jikesrvm=$jikesrvm_binding/repos/jikesrvm

ensure_empty_dir $kit_build
ensure_empty_dir $log_dir
checkout_result_repo

run_exp() {
    build_config=$1
    plan=$2
    run_config=$3
    heap_modifier=$4

    lower_case_plan_name="${plan,,}"

    # Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
    cd $jikesrvm
    build_jikesrvm_with_mmtk $jikesrvm_binding $build_config $kit_build/$plan"_x86_64_m32-linux"
    # Run
    run_id=$(run_benchmarks $log_dir $run_config $heap_modifier $history_invocations)
    # Save result
    mkdir -p $result_repo_dir/jikesrvm/$lower_case_plan_name
    cp -r $log_dir/$run_id $result_repo_dir/jikesrvm/$lower_case_plan_name
}

# NoGC
run_exp RFastAdaptiveNoGC NoGC $kit_root/configs/running-jikesrvm-nogc-complete.yml 0

# SemiSpace
run_exp RFastAdaptiveSemiSpace SemiSpace $kit_root/configs/running-jikesrvm-semispace-complete.yml 6

# MarkSweep
run_exp RFastAdaptiveMarkSweep MarkSweep $kit_root/configs/running-jikesrvm-marksweep-complete.yml 6

# Commit result
commit_result_repo 'JikesRVM Binding: '$jikesrvm_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/jikesrvm-plot.yml $result_repo_dir/jikesrvm $result_repo_dir/jikesrvm_stock $output_dir
