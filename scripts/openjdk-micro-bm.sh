set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding_trunk=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
openjdk_binding_branch=$(realpath $3)
mmtk_core_branch=$(realpath $4)
output_file=$(realpath $5)

openjdk_trunk_rev=$(git -C $openjdk_binding_trunk rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
openjdk_branch_rev=$(git -C $openjdk_binding_branch rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# microbm path
microbm_root=$kit_root/microbm
rebench_root=$kit_root/ReBench

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

# Build for trunk
ensure_empty_dir $openjdk_binding_trunk/repos/mmtk-core
cp -r $mmtk_core_trunk/* $openjdk_binding_trunk/repos/mmtk-core/
# SemiSpace
build_openjdk_with_mmtk $openjdk_binding_trunk semispace release $kit_build/jdk-mmtk-trunk-semispace

# Build for branch
ensure_empty_dir $openjdk_binding_branch/repos/mmtk-core
cp -r $mmtk_core_branch/* $openjdk_binding_branch/repos/mmtk-core/
# SemiSpace
build_openjdk_with_mmtk $openjdk_binding_branch semispace release $kit_build/jdk-mmtk-branch-semispace

# Build MicroBM
cd $microbm_root
mvn clean install
rm -f ci.data

# install rebench
start_venv $microbm_root/venv
pip install $rebench_root

echo "OpenJDK Micro Benchmarks" >> $output_file
echo "===" >> $output_file

echo "* binding_trunk: [$openjdk_trunk_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_trunk_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* binding_branch: [$openjdk_branch_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_branch_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

python ../scripts/rebench_report.py rebench microbm.conf CI_SemiSpace >> $output_file