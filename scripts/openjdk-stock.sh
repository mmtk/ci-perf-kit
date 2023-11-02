set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_path=$(realpath $1)

# Build
ensure_empty_dir $kit_build
ensure_empty_dir $log_dir
checkout_result_repo

build_openjdk_with_features $openjdk_path release $kit_build/jdk-stock zgc

ln -s $kit_build/jdk-stock $kit_build/jdk-epsilon
ln -s $kit_build/jdk-stock $kit_build/jdk-g1
ln -s $kit_build/jdk-stock $kit_build/jdk-zgc
ln -s $kit_build/jdk-stock $kit_build/jdk-parallelgc
ln -s $kit_build/jdk-stock $kit_build/jdk-serialgc
ln -s $kit_build/jdk-stock $kit_build/jdk-cms

# Run
run1_id=$(run_benchmarks $log_dir $kit_root/configs/running-openjdk-stock-nogc.yml 0 $stock_invocations)
run2_id=$(run_benchmarks $log_dir $kit_root/configs/running-openjdk-stock-other.yml 6 $stock_invocations)

# Save result
mkdir -p $result_repo_dir/openjdk_stock
merge_runs $run1_id $run2_id $result_repo_dir/openjdk_stock

# Make sure this is commented out during testing
commit_result_repo 'OpenJDK Stock GC'
