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
    ./bin/buildit localhost $plan -quick --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src --m32

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
    bin/buildit localhost $plan -quick --answer-yes --m32

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

# build_openjdk ’binding_path' 'debug_level' 'build_path'
build_openjdk_with_mmtk() {
    binding_path=$1
    debug_level=$2
    build_path=$3

    openjdk_path=$binding_path/repos/openjdk

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
    make images CONF=linux-x86_64-normal-server-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk

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
    make images CONF=linux-x86_64-normal-server-$DEBUG_LEVEL

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
    make images CONF=linux-x86_64-normal-server-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/linux-x86_64-normal-server-$DEBUG_LEVEL $build_path
}

# run_benchmarks 'log_dir' 'config' 'heap_modifier'
# heap_modifier=0 means we won't set heap size based on min heap. This is used for NoGC which we set heap size to the maximum instead of a multiple of min heap.
run_benchmarks() {
    outdir=$1
    config=$2
    heap_modifier=$3

    invocations=1

    cd $kit_root

    # Check if heap_modifier is 0
    if [ "$heap_modifier" -eq 0 ]; then
        output=$(running runbms $1 $2 -i $invocations)
    else
        output=$(running runbms $1 $2 -s $heap_modifier -i $invocations)
    fi

    # output is something like: 'Run id: fox-2020-05-13-Wed-124656'. Extract the run id.
    run_id=$(echo $output | cut -d ' ' -f 3)

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

    virtualenv $venv_path
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

# merge_runs 'run1' 'run2' 'dest'
# Copy $log_dir/run1 to dest/, then copy the contents in $log_dir/run2 to dest/run1
merge_runs() {
    run1=$1
    run2=$2
    dest=$3

    cp -r $log_dir/$run1 $dest
    cp -r $log_dir/$run2/* $dest/$run1/
}
