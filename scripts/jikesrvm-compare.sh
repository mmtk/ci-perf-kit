set -ex

# include common.sh
. $(dirname "$0")/common.sh

jikesrvm_binding_trunk=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
jikesrvm_binding_branch=$(realpath $3)
mmtk_core_branch=$(realpath $4)
output_file=$(realpath -m $5)

jikesrvm_trunk_rev=$(git -C $jikesrvm_binding_trunk rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
jikesrvm_branch_rev=$(git -C $jikesrvm_binding_branch rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# JikesRVM root
jikesrvm_trunk=$jikesrvm_binding_trunk/repos/jikesrvm
jikesrvm_branch=$jikesrvm_binding_branch/repos/jikesrvm

# Edit jikesrvm binding Cargo.toml to use local path for mmtk core - note: this makes this script not repeatable
jikesrvm_binding_use_local_mmtk $jikesrvm_binding_trunk
if [ "$jikesrvm_binding_branch" != "$jikesrvm_binding_trunk" ]; then
    jikesrvm_binding_use_local_mmtk $jikesrvm_binding_branch
fi

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
ensure_empty_dir $kit_build
ensure_empty_dir $log_dir

# Trunk
rm -rf $jikesrvm_binding_trunk/repos/mmtk-core
ln -sfn $mmtk_core_trunk $jikesrvm_binding_trunk/repos/mmtk-core

# Branch
rm -rf $jikesrvm_binding_branch/repos/mmtk-core
ln -sfn $mmtk_core_branch $jikesrvm_binding_branch/repos/mmtk-core

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

run_exp() {
    build_config=$1
    plan=$2
    run_config=$3
    heap_modifier=$4

    cd $jikesrvm_trunk
    build_jikesrvm_with_mmtk $jikesrvm_binding_trunk $build_config $kit_build/$plan"_Trunk_x86_64_m32-linux"

    cd $jikesrvm_branch
    build_jikesrvm_with_mmtk $jikesrvm_binding_branch $build_config $kit_build/$plan"_Branch_x86_64_m32-linux"

    run_id=$(run_benchmarks $log_dir $run_config $heap_modifier $compare_invocations)
    python $kit_root/scripts/compare_report.py $log_dir/$run_id $plan $plan"_Trunk" $plan"_Branch" $compare_invocations >> $output_file
}

# NoGC
run_exp RFastAdaptiveNoGC NoGC $kit_root/configs/running-jikesrvm-nogc-compare.yml 0
# SemiSpace
run_exp RFastAdaptiveSemiSpace SemiSpace $kit_root/configs/running-jikesrvm-semispace-compare.yml 6
# MarkSweep
run_exp RFastAdaptiveMarkSweep MarkSweep $kit_root/configs/running-jikesrvm-marksweep-compare.yml 6
