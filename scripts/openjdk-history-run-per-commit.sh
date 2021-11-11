set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding=$(realpath $1)
output_dir=$(realpath -m $2)
openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk

ensure_empty_dir $kit_build
checkout_result_repo

# --- Build ---
cd $openjdk
build_openjdk_with_mmtk $openjdk_binding release $kit_build/jdk-mmtk

# --- Run ---
cd $kit_root
saved_log_dir=$result_repo_dir/openjdk/per_commit

# Run For NoGC
nogc_run_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/openjdk/history/nogc.yml $history_invocations)
# Save result
mkdir -p $saved_log_dir/nogc
cp -r $log_dir/$nogc_run_id $saved_log_dir/nogc

# Run For GenImmix
genimmix_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/genimmix.yml $history_invocations)
# Save result
mkdir -p $saved_log_dir/genimmix
cp -r $log_dir/$genimmix_run_id $saved_log_dir/genimmix

# Run For Immix
ix_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/immix_stress.yml $history_invocations)
# Save result
mkdir -p $saved_log_dir/immix_stress
cp -r $log_dir/$ix_run_id $saved_log_dir/immix_stress

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
