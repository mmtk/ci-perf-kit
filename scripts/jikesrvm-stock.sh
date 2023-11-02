set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
ensure_empty_dir $log_dir
checkout_result_repo

cd $jikesrvm_path

build_jikesrvm $jikesrvm_path FastAdaptiveNoGC $kit_build/JavaMMTk_NoGC_x86_64_m32-linux
build_jikesrvm $jikesrvm_path FastAdaptiveSemiSpace $kit_build/JavaMMTk_SemiSpace_x86_64_m32-linux
build_jikesrvm $jikesrvm_path FastAdaptiveMarkSweep $kit_build/JavaMMTk_MarkSweep_x86_64_m32-linux

# Run
run1_id=$(run_benchmarks $log_dir $kit_root/configs/running-jikesrvm-stock-nogc.yml 0 $stock_invocations)
run2_id=$(run_benchmarks $log_dir $kit_root/configs/running-jikesrvm-stock-other.yml 6 $stock_invocations)

# Save result
mkdir -p $result_repo_dir/jikesrvm_stock
merge_runs $run1_id $run2_id $result_repo_dir/jikesrvm_stock

# Make sure this is commented out during testing
commit_result_repo 'JikesRVM Stock GC'
