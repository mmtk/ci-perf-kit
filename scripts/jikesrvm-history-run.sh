set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_binding=$(realpath $1)
output_dir=$(realpath -m $2)
jikesrvm_rev=$(git -C $jikesrvm_binding rev-parse HEAD)

# JikesRVM root
jikesrvm=$jikesrvm_binding/repos/jikesrvm

ensure_empty_dir $kit_build
checkout_result_repo

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir

# NoGC
build_jikesrvm_with_mmtk $jikesrvm_binding RFastAdaptiveNoGC $kit_build/NoGC_x86_64_m32-linux
# Run for NoGC
nogc_run_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/jikesrvm/history/nogc.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/jikesrvm/nogc
cp -r $log_dir/$nogc_run_id $result_repo_dir/jikesrvm/nogc

# SemiSpace
build_jikesrvm_with_mmtk $jikesrvm_binding RFastAdaptiveSemiSpace $kit_build/SemiSpace_x86_64_m32-linux
# Run for SemiSpace
ss_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/jikesrvm/history/semispace.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/jikesrvm/semispace
cp -r $log_dir/$ss_run_id $result_repo_dir/jikesrvm/semispace

# MarkSweep
build_jikesrvm_with_mmtk $jikesrvm_binding RFastAdaptiveMarkSweep $kit_build/MarkSweep_x86_64_m32-linux
# Run for MarkSweep
ms_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/jikesrvm/history/marksweep.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/jikesrvm/marksweep
cp -r $log_dir/$ms_run_id $result_repo_dir/jikesrvm/marksweep

# Commit result
commit_result_repo 'JikesRVM Binding: '$jikesrvm_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
python3 scripts/history_report.py configs/jikesrvm-plot.yml $result_repo_dir/jikesrvm $result_repo_dir/jikesrvm_stock $output_dir
