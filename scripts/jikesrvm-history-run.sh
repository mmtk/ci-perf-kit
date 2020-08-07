set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_binding=$(realpath $1)
output_dir=$(realpath $2)
jikesrvm_rev=$(git -C $jikesrvm_binding rev-parse HEAD)

# JikesRVM root
jikesrvm=$jikesrvm_binding/repos/jikesrvm

ensure_empty_dir $kit_build
checkout_result_repo

# Copy probes
ensure_empty_dir $kit_root/running/bin/probes
cp $kit_root/probes/probes.jar $kit_root/running/bin/probes/

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
cd $jikesrvm

# NoGC
build_jikesrvm_with_mmtk $jikesrvm_binding RFastAdaptiveNoGC $kit_build/NoGC_x86_64-linux
# Run for NoGC
nogc_run_id=$(run_benchmarks $kit_root/configs/RunConfig-JikesRVM-NoGC-Complete.pm)
# Save result
mkdir -p $result_repo_dir/jikesrvm/nogc
cp -r $kit_root/running/results/log/$nogc_run_id $result_repo_dir/jikesrvm/nogc

# SemiSpace
build_jikesrvm_with_mmtk $jikesrvm_binding RFastAdaptiveSemiSpace $kit_build/SemiSpace_x86_64-linux
# Run for SemiSpace
ss_run_id=$(run_benchmarks $kit_root/configs/RunConfig-JikesRVM-SemiSpace-Complete.pm)
# Save result
mkdir -p $result_repo_dir/jikesrvm/semispace
cp -r $log_dir/$ss_run_id $result_repo_dir/jikesrvm/semispace

# Commit result
commit_result_repo 'JikesRVM Binding: '$jikesrvm_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py $result_repo_dir/jikesrvm $output_dir jikesrvm
