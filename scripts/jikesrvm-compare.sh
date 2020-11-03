set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_binding_trunk=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
jikesrvm_binding_branch=$(realpath $3)
mmtk_core_branch=$(realpath $4)
output_file=$(realpath $5)

jikesrvm_trunk_rev=$(git -C $jikesrvm_binding_trunk rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
jikesrvm_branch_rev=$(git -C $jikesrvm_binding_branch rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# JikesRVM root
jikesrvm_trunk=$jikesrvm_binding_trunk/repos/openjdk
jikesrvm_branch=$jikesrvm_binding_branch/repos/openjdk

# Edit jikesrvm binding Cargo.toml to use local path for mmtk core - note: this makes this script not repeatable
jikesrvm_binding_use_local_mmtk $jikesrvm_binding_trunk
if [ "$jikesrvm_binding_branch" != "$jikesrvm_binding_trunk" ]; then
    jikesrvm_binding_use_local_mmtk $jikesrvm_binding_branch
fi

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
ensure_empty_dir $kit_build

# Trunk
ensure_empty_dir $jikesrvm_binding_trunk/repos/mmtk-core
cp -r $mmtk_core_trunk/* $jikesrvm_binding_trunk/repos/mmtk-core/
build_jikesrvm_with_mmtk $jikesrvm_binding_trunk RFastAdaptiveNoGC $kit_build/NoGC_Trunk_x86_64-linux
build_jikesrvm_with_mmtk $jikesrvm_binding_trunk RFastAdaptiveSemiSpace $kit_build/SemiSpace_Trunk_x86_64-linux

# Branch
ensure_empty_dir $jikesrvm_binding_branch/repos/mmtk-core
cp -r $mmtk_core_branch/* $jikesrvm_binding_branch/repos/mmtk-core/
build_jikesrvm_with_mmtk $jikesrvm_binding_branch RFastAdaptiveNoGC $kit_build/NoGC_Branch_x86_64-linux
build_jikesrvm_with_mmtk $jikesrvm_binding_branch RFastAdaptiveSemiSpace $kit_build/SemiSpace_Branch_x86_64-linux

# Run
cd $kit_root

echo "JikesRVM" >> $output_file
echo "====" >> $output_file

echo "* binding_trunk: [$jikesrvm_trunk_rev](https://github.com/mmtk/mmtk-jikesrvm/commit/$jikesrvm_trunk_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* binding_branch: [$jikesrvm_branch_rev](https://github.com/mmtk/mmtk-jikesrvm/commit/$jikesrvm_branch_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

# Python venv
start_venv python-env
pip3 install -r scripts/requirements.txt

# Run for NoGC
nogc_run_id=$(run_benchmarks $kit_root/configs/RunConfig-JikesRVM-NoGC-FastCompare.pm)
# Result for NoGC
python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$nogc_run_id NoGC NoGC_Trunk NoGC_Branch 40 >> $output_file

# Run for SemiSpace
ss_run_id=$(run_benchmarks $kit_root/configs/RunConfig-JikesRVM-SemiSpace-FastCompare.pm)
# Result for SemiSpace
python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$ss_run_id SemiSpace SemiSpace_Trunk SemiSpace_Branch 40 >> $output_file
