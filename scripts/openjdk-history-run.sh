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
mkdir -p $kit_build
rm -rf $kit_build/*
# where we put results
result_dir=$kit_root/result_repo

# Expect these env vars
# RESULT_REPO
# RESULT_REPO_BRANCH
# RESULT_REPO_ACCESS_TOKEN
rm -rf $result_dir
git clone https://$RESULT_REPO_ACCESS_TOKEN@github.com/$RESULT_REPO.git $result_dir --branch=$RESULT_REPO_BRANCH

# Copy probes
mkdir -p $kit_root/running/bin/probes
cp $kit_root/probes/probes.jar $kit_root/running/bin/probes/

# Edit openjdk binding Cargo.toml to use access token
sed -i 's/ssh:\/\/git@github.com\/mmtk/https:\/\/qinsoon:'$CI_ACCESS_TOKEN'@github.com\/mmtk/g' $openjdk_binding/mmtk/Cargo.toml

# Build
cd $openjdk
export DEBUG_LEVEL=release

# NoGC
export MMTK_PLAN=nogc
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-nogc
# Run For NoGC
cp $kit_root/configs/RunConfig-OpenJDK-NoGC-Complete.pm $kit_root/running/bin/RunConfig.pm
nogc_output=$($kit_root/running/bin/runbms 16 16)
nogc_run_id=$(echo $nogc_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'
# Save result
mkdir -p $result_dir/openjdk/nogc
cp -r $kit_root/running/results/log/$nogc_run_id $result_dir/openjdk/nogc

# SemiSpace
export MMTK_PLAN=semispace
sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
cp -r $openjdk/build/linux-x86_64-normal-server-$DEBUG_LEVEL/ $kit_build/jdk-mmtk-semispace
# Run For SemiSpace
cp $kit_root/configs/RunConfig-OpenJDK-SemiSpace-Complete.pm $kit_root/running/bin/RunConfig.pm
ss_output=$($kit_root/running/bin/runbms 16 16)
ss_run_id=$(echo $ss_output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'
# Save result
mkdir -p $result_dir/openjdk/semispace
cp -r $kit_root/running/results/log/$ss_run_id $result_dir/openjdk/semispace

# Commit result
cd $result_dir
git add .
git -c user.name='github-actions' -c user.email=bot@noreply.github.com commit -m 'OpenJDK Binding: '$openjdk_rev
git pull --rebase # pull any new commit (if any)
git push
