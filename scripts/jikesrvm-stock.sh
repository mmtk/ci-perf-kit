set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
checkout_result_repo

cd $jikesrvm_path

build_jikesrvm $jikesrvm_path FastAdaptiveNoGC $kit_build/JavaMMTk_NoGC_x86_64_m32-linux
build_jikesrvm $jikesrvm_path FastAdaptiveSemiSpace $kit_build/JavaMMTk_SemiSpace_x86_64_m32-linux
build_jikesrvm $jikesrvm_path FastAdaptiveMarkSweep $kit_build/JavaMMTk_MarkSweep_x86_64_m32-linux

# Run
run1_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/jikesrvm/stock/nogc.yml $stock_invocations)
run2_id=$(run_benchmarks $log_dir $kit_root/configs-ng/jikesrvm/stock/other.yml $stock_invocations)

# Save result
mkdir -p $result_repo_dir/jikesrvm_stock
# Copy run1
cp -r $log_dir/$run1_id $result_repo_dir/jikesrvm_stock
# Copy the logs in run2 to the run1 folder (pretending they are the same run)
cp -r $log_dir/$run2_id/* $result_repo_dir/jikesrvm_stock/$run1_id/

# Make sure this is commented out during testing
commit_result_repo 'JikesRVM Stock GC'
