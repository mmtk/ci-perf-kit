# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/build
# where we put all the scripts
kit_script=$kit_root/scripts
# where we put all the configs
config_dir=$kit_root/configs
# where result logs are stored
log_dir=$kit_root/logs-ng
# where we put results
result_repo_dir=$kit_root/result_repo

# compare benchmarking invocations
compare_invocations=2
# history benchmarking invocations
history_invocations=2
# stock GC benchmarking invocations
stock_invocations=2

# ensure_env 'var_name'
ensure_env() {
    env_var=$1

    if ! [[ -v $env_var ]]; then
        echo "Environment Variable "$env_var" is required. "
        exit 1
    fi
}

# build_jikesrvm_with_mmtk 'binding_path' 'plan' 'build_path'
# Env: JAVA_HOME
build_jikesrvm_with_mmtk() {
    ensure_env JAVA_HOME

    binding_path=$1
    plan=$2
    build_path=$3 # put the build here

    jikesrvm_path=$binding_path/repos/jikesrvm

    cd $jikesrvm_path

    # build
    python2 scripts/testMMTk.py -g $plan -j $JAVA_HOME --build-only -- -quick --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src --m32

    # copy to build_path
    cp -r $jikesrvm_path'/dist/'$plan'_x86_64_m32-linux' $build_path/
}

# build_jikesrvm 'jikesrvm_path' 'plan' 'build_path'
# Env: JAVA_HOME
build_jikesrvm() {
    ensure_env JAVA_HOME

    jikesrvm_path=$1
    plan=$2
    build_path=$3

    cd $jikesrvm_path

    # build
    bin/buildit localhost $plan -j $JAVA_HOME -quick --m32

    # copy to build_path
    cp -r $jikesrvm_path'/dist/'$plan'_x86_64_m32-linux' $build_path/
}

# openjdk_binding_use_local_mmtk 'binding_path'
openjdk_binding_use_local_mmtk() {
    binding_path=$1

    sed -i s/^mmtk[[:space:]]=/#ci:mmtk=/g $binding_path/mmtk/Cargo.toml
    sed -i s/^#[[:space:]]mmtk/mmtk/g $binding_path/mmtk/Cargo.toml
}

# jikesrvm_binding_use_local_mmtk 'binding_path'
jikesrvm_binding_use_local_mmtk() {
    binding_path=$1

    sed -i s/^mmtk[[:space:]]=/#ci:mmtk=/g $binding_path/mmtk/Cargo.toml
    sed -i s/^#[[:space:]]mmtk/mmtk/g $binding_path/mmtk/Cargo.toml
}

# build_openjdk ’binding_path' 'plan' 'debug_level' 'build_path'
build_openjdk_with_mmtk() {
    binding_path=$1
    plan=$2
    debug_level=$3
    build_path=$4

    openjdk_path=$binding_path/repos/openjdk

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    # export MMTK_PLAN=$plan
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
    make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk

    # copy to build_path
    cp -r $openjdk_path/build/linux-x86_64-normal-server-$DEBUG_LEVEL $build_path
}

# build_openjdk 'openjdk_path' 'debug_level' 'build_path'
build_openjdk() {
    openjdk_path=$1
    debug_level=$2
    build_path=$3

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL --with-jvm-features=zgc
    make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/linux-x86_64-normal-server-$DEBUG_LEVEL $build_path
}

# build_openjdk_with_features 'openjdk_path' 'debug_level' 'build_path' 'features'
build_openjdk_with_features() {
    openjdk_path=$1
    debug_level=$2
    build_path=$3
    features=$4

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL --with-jvm-features=$features
    make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/linux-x86_64-normal-server-$DEBUG_LEVEL $build_path
}

# run_benchmarks 'log_dir' 'config' 'invocations'
run_benchmarks() {
    outdir=$1
    config=$2
    invocations=$3

    cd $kit_root

    # factor 8 8 gives 6x minheap as heap size
    output=$(running runbms $1 $2 8 8 -i $3)
    # Get the second line
    run_id=$(echo $output | cut -d ' ' -f 3)

    echo $run_id
}

# To run benchmarks with this, the config should provide a specific heap size for each build.
# Min heap size or a multiple of min heap size won't be applied to each benchmark. This would
# mostly be used for NoGC (for which we run with largest possible heap size)
# run_benchmarks_custom_heap 'log_dir' 'config' 'invocations'
run_benchmarks_custom_heap() {
    outdir=$1
    config=$2
    invocations=$3

    cd $kit_root

    # factor 8 4 gives roughly 3x minheap as heap size
    output=$(running runbms $1 $2 -i $3)
    # Get the second line
    run_id=$(echo $output | cut -d ' ' -f 3)

    echo $run_id
}

# merge_runs 'run1' 'run2' 'dest'
# Copy run1 to dest/, then copy the contents in run2 to dest/run1
merge_runs() {
    run1=$1
    run2=$2
    dest=$3

    cp -r $run1 $dest
    cp -r $run2/* $dest/$run1/
}

# prepare_dir 'path'
# Make sure the dir exists and is empty
ensure_empty_dir() {
    path=$1

    mkdir -p $path
    rm -rf $path/*
}

# start_venv 'venv_path'
start_venv() {
    venv_path=$1

    ensure_empty_dir $venv_path
    python3 -m venv $venv_path
    source $venv_path/bin/activate
}

leave_venv() {
    deactivate
}

# Env: RESULT_REPO_ACCESS_TOKEN, RESULT_REPO, RESULT_REPO_BRANCH
checkout_result_repo() {
    ensure_env RESULT_REPO
    ensure_env RESULT_REPO_BRANCH
    
    rm -rf $result_repo_dir
    # Use this for local testing
    # git clone ssh://git@github.com/$RESULT_REPO.git $result_repo_dir --branch=$RESULT_REPO_BRANCH
    git clone https://$RESULT_REPO_ACCESS_TOKEN@github.com/$RESULT_REPO.git $result_repo_dir
    git --git-dir $result_repo_dir/.git checkout -B $RESULT_REPO_BRANCH
}

# commit_result_repo_dir 'message'
commit_result_repo() {
    if [[ -z $SKIP_UPLOAD_RESULT ]]; then
        message=$1

        cd $result_repo_dir

        git add .
        git commit -m "$message"
        git pull --rebase # pull any new commit (if any)
        git push    
    else
        echo "SKIP_UPLOAD_RESULT is set, skip uploading result"
    fi
}

# start venv, and install running-ng
start_venv $kit_root/python-env
pip3 install -e $kit_root/running-ng
pip3 install -r $kit_root/scripts/requirements.txt