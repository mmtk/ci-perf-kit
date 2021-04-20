set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
# checkout_result_repo

cd $jikesrvm_path

build_jikesrvm $jikesrvm_path FastAdaptiveNoGC $kit_build/JavaMMTk_NoGC_x86_64-linux
build_jikesrvm $jikesrvm_path FastAdaptiveSemiSpace $kit_build/JavaMMTk_SemiSpace_x86_64-linux

# Run
stock_run_id=$(run_benchmarks $kit_root/configs/RunConfig-JikesRVM-Stock.pm)

# Save result
mkdir -p $result_repo_dir/jikesrvm_stock
cp -r $kit_root/running/results/log/$stock_run_id $result_repo_dir/jikesrvm_stock

# Make sure this is commented out during testing
# commit_result_repo 'JikesRVM Stock GC'
