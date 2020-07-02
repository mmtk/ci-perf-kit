set -ex
jikesrvm_binding=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
mmtk_core_branch=$(realpath $3)
output_file=$(realpath $4)

jikesrvm_rev=$(git -C $jikesrvm_binding rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# JikesRVM root
jikesrvm=$jikesrvm_binding/repos/jikesrvm
# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/running/build
mkdir -p $kit_build
rm -rf $kit_build/*

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
cd $jikesrvm

# Build for trunk
rsync -avLe $mmtk_core_trunk/* $jikesrvm_binding/repos/mmtk-core
# NoGC
python scripts/testMMTk.py -g RFastAdaptiveNoGC -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveNoGC_x86_64-linux $kit_build/NoGC_Trunk_x86_64-linux/
# SemiSpace
python scripts/testMMTk.py -g RFastAdaptiveSemiSpace -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveSemiSpace_x86_64-linux $kit_build/SemiSpace_Trunk_x86_64-linux/

# Build for branch
rsync -avLe $mmtk_core_branch/* $jikesrvm_binding/repos/mmtk-core
# NoGC
python scripts/testMMTk.py -g RFastAdaptiveNoGC -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveNoGC_x86_64-linux $kit_build/NoGC_Branch_x86_64-linux/
# SemiSpace
python scripts/testMMTk.py -g RFastAdaptiveSemiSpace -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveSemiSpace_x86_64-linux $kit_build/SemiSpace_Branch_x86_64-linux/

# Run
cd $kit_root
mkdir -p $kit_root/running/bin/probes
cp $kit_root/probes/probes.jar $kit_root/running/bin/probes/

echo "JikesRVM" >> $output_file
echo "====" >> $output_file

echo "* binding: [$jikesrvm_rev](https://github.com/mmtk/mmtk-jikesrvm/commit/$jikesrvm_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

# Run for NoGC
cp $kit_root/configs/RunConfig-JikesRVM-NoGC-FastCompare.pm $kit_root/running/bin/RunConfig.pm
nogc_output=$($kit_root/running/bin/runbms 16 16)
nogc_run_id=$(echo $nogc_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

# Result for NoGC
python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$nogc_run_id NoGC NoGC_Trunk NoGC_Branch 80 >> $output_file

# # Run for SemiSpace
cp $kit_root/configs/RunConfig-JikesRVM-SemiSpace-FastCompare.pm $kit_root/running/bin/RunConfig.pm
ss_output=$($kit_root/running/bin/runbms 16 16)
ss_run_id=$(echo $ss_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

# # Result for SemiSpace
python $kit_root/scripts/compare_report.py $kit_root/running/results/log/$ss_run_id SemiSpace SemiSpace_Trunk SemiSpace_Branch 80 >> $output_file
