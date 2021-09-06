set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
checkout_result_repo

build_openjdk_with_features $openjdk_path release $kit_build/jdk-stock zgc

# Run
cd $kit_root

stock_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/stock/base.yml $stock_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk_stock
cp -r $log_dir/$stock_run_id $result_repo_dir/openjdk_stock

# Make sure this is commented out during testing
commit_result_repo 'OpenJDK Stock GC'
