set -ex
openjdk_binding=$(realpath $1)
output_dir=$(realpath $2)
openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk
# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/running/build
# where we put results
result_dir=$kit_root/result_repo

# Expect these env vars
# RESULT_REPO
# RESULT_REPO_BRANCH
# RESULT_REPO_ACCESS_TOKEN
rm -rf $result_dir
# For test locally
# git clone ssh://git@github.com/$RESULT_REPO.git $result_dir --branch=$RESULT_REPO_BRANCH
git clone https://$RESULT_REPO_ACCESS_TOKEN@github.com/$RESULT_REPO.git $result_dir --branch=$RESULT_REPO_BRANCH

# Build probe
cd $kit_root/probes/openjdk
make
cd $kit_root/probes/rust_mmtk
make

# Build
mkdir -p $kit_build
rm -rf $kit_build/*
cd $openjdk
export DEBUG_LEVEL=release

# NoGC
export MMTK_PLAN=nogc
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-nogc
# SemiSpace
export MMTK_PLAN=semispace
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-semispace
# Stock OpenJDK
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-stock
# Symlink
ln -s $kit_build/jdk-stock $kit_build/jdk-epsilon
ln -s $kit_build/jdk-stock $kit_build/jdk-g1

# Run
cp $kit_root/configs/RunConfig-OpenJDK-Mutator-History.pm $kit_root/running/bin/RunConfig.pm
mu_output=$($kit_root/running/bin/runbms 16 16)
mu_run_id=$(echo $mu_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

# Save result
mkdir -p $result_dir/mutator
cp -r $kit_root/running/results/log/$mu_run_id $result_dir/mutator
# Commit result
cd $result_dir
git add .
git commit -m 'Mutator(OpenJDK) Binding: '$openjdk_rev
git pull --rebase
git push

# plot result
mkdir -p $output_dir
rm -f $output_dir/*

cd $kit_root
python3 -m venv python-env
source python-env/bin/activate
pip3 install -r scripts/requirements.txt
python3 scripts/mutator_report.py $result_dir/mutator $output_dir