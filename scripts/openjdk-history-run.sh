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
build_openjdk_with_mmtk $openjdk_binding _ release $kit_build/jdk-mmtk

# --- Run ---
cd $kit_root

# Run For NoGC
nogc_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/nogc.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk/nogc
cp -r $log_dir/$nogc_run_id $result_repo_dir/openjdk/nogc

# Run for SemiSpace
ss_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/semispace.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk/semispace
cp -r $log_dir/$ss_run_id $result_repo_dir/openjdk/semispace

# Run For GenCopy
gencopy_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/gencopy.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk/gencopy
cp -r $log_dir/$gencopy_run_id $result_repo_dir/openjdk/gencopy

# Run For MarkSweep
ms_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/marksweep.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk/marksweep
cp -r $log_dir/$ms_run_id $result_repo_dir/openjdk/marksweep

# Run For Immix
ix_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/history/immix.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/openjdk/immix
cp -r $log_dir/$ix_run_id $result_repo_dir/openjdk/immix

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
