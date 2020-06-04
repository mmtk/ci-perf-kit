set -ex
jikesrvm_binding=$(realpath $1)
output_dir=$(realpath $2)
jikesrvm_rev=$(git -C $jikesrvm_binding rev-parse HEAD)

# JikesRVM root
jikesrvm=$jikesrvm_binding/repos/jikesrvm
# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/running/build
mkdir -p $kit_build
rm -rf $kit_build/*
# where we put results
result_dir=$kit_root/result_repo

# Expect these env vars
# RESULT_REPO
# RESULT_REPO_BRANCH
# RESULT_REPO_ACCESS_NAME
# RESULT_REPO_ACCESS_TOKEN
rm -rf $result_dir
git clone https://$RESULT_REPO_ACCESS_TOKEN@github.com/$RESULT_REPO.git $result_dir --branch=$RESULT_REPO_BRANCH

# Copy probes
mkdir -p $kit_root/running/bin/probes
cp $kit_root/probes/probes.jar $kit_root/running/bin/probes/

# Build - JikesRVM buildit script requires current dir to be JikesRVM root dir
cd $jikesrvm

# NoGC
python scripts/testMMTk.py -g RFastAdaptiveNoGC -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveNoGC_x86_64-linux $kit_build/NoGC_x86_64-linux/
# Run for NoGC
cp $kit_root/configs/RunConfig-JikesRVM-NoGC-Complete.pm $kit_root/running/bin/RunConfig.pm
nogc_output=$($kit_root/running/bin/runbms 16 16)
nogc_run_id=$(echo $nogc_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'
# Save result
mkdir -p $result_dir/jikesrvm/nogc
cp -r $kit_root/running/results/log/$nogc_run_id $result_dir/jikesrvm/nogc

# SemiSpace
python scripts/testMMTk.py -g RFastAdaptiveSemiSpace -j $JAVA_HOME --build-only -- --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src
cp -r $jikesrvm/dist/RFastAdaptiveSemiSpace_x86_64-linux $kit_build/SemiSpace_x86_64-linux/
# Run for SemiSpace
cp $kit_root/configs/RunConfig-JikesRVM-SemiSpace-Complete.pm $kit_root/running/bin/RunConfig.pm
ss_output=$($kit_root/running/bin/runbms 16 16)
ss_run_id=$(echo $ss_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'
# Save result
mkdir -p $result_dir/jikesrvm/semispace
cp -r $kit_root/running/results/log/$ss_run_id $result_dir/jikesrvm/semispace

# Commit result
cd $result_dir
git add .
git -c user.name='github-actions' -c user.email=bot@noreply.github.com -commit -m 'JikesRVM Binding: '$jikesrvm_rev
git push

# plot result
mkdir -p $output_dir

cd $kit_root
python3 -m venv python-env
source python-env/bin/activate
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py $result_dir/jikesrvm $output_dir
