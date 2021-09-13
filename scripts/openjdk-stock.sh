set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
checkout_result_repo

build_openjdk_with_features $openjdk_path release $kit_build/jdk-stock zgc

# Run
run1_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/openjdk/stock/nogc.yml $stock_invocations)
run2_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/stock/other.yml $stock_invocations)

# Save result
mkdir -p $result_repo_dir/openjdk_stock
merge_runs $log_dir/$run1_id $log_dir/$run2_id $result_repo_dir

# Make sure this is commented out during testing
commit_result_repo 'OpenJDK Stock GC'
