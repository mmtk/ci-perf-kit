# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds
kit_build=$kit_root/running/build
# where we put all the scripts
kit_script=$kit_root/scripts
# where we put all the configs
config_dir=$kit_root/configs
# where result logs are stored
log_dir=$kit_root/running/results/log
# where we put results
result_repo_dir=$kit_root/result_repo

# ensure_env 'var_name'
ensure_env() {
    env_var=$1

    if ! [[ -v $env_var ]]; then
        echo "Environment Variable "$env_var" is required. "
        exit 1
    fi
}

# build_jikesrvm 'binding_path' 'plan' 'build_path'
# Env: JAVA_HOME
build_jikesrvm_with_mmtk() {
    ensure_env JAVA_HOME

    binding_path=$1
    plan=$2
    build_path=$3 # put the build here

    jikesrvm_path=$binding_path/repos/jikesrvm

    cd $jikesrvm_path

    # build
    python scripts/testMMTk.py -g $plan -j $JAVA_HOME --build-only -- -quick --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src

    # copy to build_path
    cp -r $jikesrvm_path'/dist/'$plan'_x86_64-linux' $build_path/
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
    export MMTK_PLAN=$plan
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
    export DEBUG_LEVEl=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
    make CONF=linux-x86_64-normal-server-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/linux-x86_64-normal-server-$DEBUG_LEVEL $build_path
}

# run_benchmarks 'config'
run_benchmarks() {
    config=$1

    cp $config $kit_root/running/bin/RunConfig.pm
    output=$($kit_root/running/bin/runbms 16 16)
    run_id=$(echo $output | cut -d ' ' -f 3) # output is something like: 'Run id: fox-2020-05-13-Wed-124656'

    echo $run_id
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
    git clone https://$RESULT_REPO_ACCESS_TOKEN@github.com/$RESULT_REPO.git $result_repo_dir --branch=$RESULT_REPO_BRANCH
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