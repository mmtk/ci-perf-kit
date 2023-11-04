set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding_trunk=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
openjdk_binding_branch=$(realpath $3)
mmtk_core_branch=$(realpath $4)
output_file=$(realpath -m $5)

openjdk_trunk_rev=$(git -C $openjdk_binding_trunk rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
openjdk_branch_rev=$(git -C $openjdk_binding_branch rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# OpenJDK root
openjdk_trunk=$openjdk_binding_trunk/repos/openjdk
openjdk_branch=$openjdk_binding_branch/repos/openjdk

# Edit openjdk binding Cargo.toml to use local path for mmtk core - note: this makes this script not repeatable
openjdk_binding_use_local_mmtk $openjdk_binding_trunk
if [ "$openjdk_binding_branch" != "$openjdk_binding_trunk" ]; then
    openjdk_binding_use_local_mmtk $openjdk_binding_branch
fi

# Build
ensure_empty_dir $kit_build
ensure_empty_dir $kit_upload
ensure_empty_dir $log_dir

# Build for trunk
rm -rf $openjdk_binding_trunk/repos/mmtk-core
ln -sfn $mmtk_core_trunk $openjdk_binding_trunk/repos/mmtk-core
build_openjdk_with_mmtk $openjdk_binding_trunk release jdk-mmtk-trunk

# Build for branch
rm -rf $openjdk_binding_branch/repos/mmtk-core
ln -sfn $mmtk_core_branch $openjdk_binding_branch/repos/mmtk-core
build_openjdk_with_mmtk $openjdk_binding_branch release jdk-mmtk-branch

# Run
cd $kit_root

echo "OpenJDK" >> $output_file
echo "====" >> $output_file

echo "* binding_trunk: [$openjdk_trunk_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_trunk_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* binding_branch: [$openjdk_branch_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_branch_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

# Python venv
start_venv python-env
pip3 install -r scripts/requirements.txt

run_exp() {
    plan=$1
    run_config=$2
    heap_modifier=$3

    run_id=$(run_benchmarks $log_dir $kit_root/configs/$run_config $heap_modifier $compare_invocations)
    python $kit_root/scripts/compare_report.py $log_dir/$run_id $plan jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file
}

# NoGC
run_exp NoGC running-openjdk-nogc-compare.yml 0

# SemiSpace
run_exp SemiSpace running-openjdk-semispace-compare.yml 6

# GenCopy
run_exp GenCopy running-openjdk-semispace-compare.yml 6

# Immix
run_exp Immix running-openjdk-immix-compare.yml 6

# GenImmix
run_exp GenImmix running-openjdk-genimmix-compare.yml 6

# StickyImmix
run_exp StickyImmix running-openjdk-stickyimmix-compare.yml 6

# MarkSweep
run_exp MarkSweep running-openjdk-marksweep-compare.yml 6
