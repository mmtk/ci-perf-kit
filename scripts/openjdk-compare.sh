set -ex
openjdk_binding=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
mmtk_core_branch=$(realpath $3)
output_file=$(realpath $4)

openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk
# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/running/build
mkdir -p $kit_build
rm -rf $kit_build/*

# Edit openjdk binding Cargo.toml to use local path for mmtk core - note: this makes this script not repeatable
sed -i s/^mmtk[[:space:]]=/#ci:mmtk=/g $openjdk_binding/mmtk/Cargo.toml
sed -i s/^#[[:space:]]mmtk/mmtk/g $openjdk_binding/mmtk/Cargo.toml
mkdir -p $openjdk_binding/repos/mmtk-core

# Build
cd $openjdk
export DEBUG_LEVEL=release

# Build for trunk
rm -rf $openjdk_binding/repos/mmtk-core/*
cp -r $mmtk_core_trunk/* $openjdk_binding/repos/mmtk-core/
# NoGC
# export MMTK_PLAN=nogc
# sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
# make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
# cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-trunk-nogc
# SemiSpace
export MMTK_PLAN=semispace
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-trunk-semispace

# Build for branch
rm -rf $openjdk_binding/repos/mmtk-core/*
cp -r $mmtk_core_branch/* $openjdk_binding/repos/mmtk-core/
# NoGC
# export MMTK_PLAN=nogc
# sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
# make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
# cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-branch-nogc
# SemiSpace
export MMTK_PLAN=semispace
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-branch-semispace

# Run
cd $kit_root
mkdir -p $kit_root/running/bin/probes
cp $kit_root/probes/probes.jar $kit_root/running/bin/probes/

echo "OpenJDK" >> $output_file
echo "====" >> $output_file

echo "* binding: [$openjdk_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

# # Run for NoGC
# cp $kit_root/configs/RunConfig-OpenJDK-NoGC-FastCompare.pm $kit_root/running/bin/RunConfig.pm
# nogc_output=$($kit_root/running/bin/runbms 16 16)
# nogc_run_id=$(echo $nogc_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

# # Result for NoGC
# python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$nogc_run_id NoGC jdk-mmtk-trunk-nogc jdk-mmtk-branch-nogc 5 >> $output_file

# Run For SemiSpace
cp $kit_root/configs/RunConfig-OpenJDK-SemiSpace-FastCompare.pm $kit_root/running/bin/RunConfig.pm
ss_output=$($kit_root/running/bin/runbms 16 16)
ss_run_id=$(echo $ss_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

# Result for SemiSpace
python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$ss_run_id SemiSpace jdk-mmtk-trunk-semispace jdk-mmtk-branch-semispace 5 >> $output_file