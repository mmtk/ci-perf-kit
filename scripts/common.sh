# root dir of this perf kit
kit_root=$(realpath $(dirname "$0")/..)
# where we put all the builds. We run benchmarks from the build.
kit_build=$kit_root/build
# where we put all the builds for uploading. The builds here need to be small enough so we can upload them
kit_upload=$kit_root/upload/
# where we put all the scripts
kit_script=$kit_root/scripts
# where we put all the configs
config_dir=$kit_root/configs
# where result logs are stored
log_dir=$kit_root/logs-ng
# where we put results
result_repo_dir=$kit_root/result_repo

stock_invocations=20
compare_invocations=20
history_invocations=20

# Kept in sync with the "suites.dacapochopin.path" override in
# configs/running-openjdk-base.yml.
dacapochopin_jar=/usr/share/benchmarks/dacapo/dacapo-23.11-MR2-chopin.jar

# OpenJDK's build system names each build's output directory
# "$openjdk_build_conf-<debug-level>" (e.g. "linux-x86_64-server-release").
# This is only the "make CONF=" prefix, not the debug level suffix - callers
# append "-$debug_level" themselves. This changed between JDK versions (JDK
# 11 used "linux-x86_64-normal-server", JDK 21 dropped "normal" - confirmed
# against mmtk-openjdk's own .github/scripts/ci-build.sh on each branch), so
# it's factored out here to make a future JDK bump a one-line change instead
# of finding every "make CONF=..."/"build/linux-x86_64-..." call site again.
openjdk_build_conf=linux-x86_64-server

# Cargo's libgit2 git fetcher only tries ssh-agent, not a default ~/.ssh key,
# so it can fail to fetch git dependencies (e.g. mmtk-core) even when the
# system git CLI authenticates fine. Delegate to the system git CLI instead.
export CARGO_NET_GIT_FETCH_WITH_CLI=true

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
    build_config=$2
    build_path=$3 # put the build here

    jikesrvm_path=$binding_path/repos/jikesrvm

    cd $jikesrvm_path

    # build
    ./bin/buildit localhost $build_config -quick --answer-yes --use-third-party-heap=../.. --use-third-party-build-configs=../../jikesrvm/build/configs --use-external-source=../../jikesrvm/rvm/src --m32

    # Copy to build_path
    cp -r $jikesrvm_path'/dist/'$build_config'_x86_64_m32-linux' $kit_build/$build_path
    # Directly copy to upload. JikesRVM builds are small enough that we can directly upload.
    cp -r $jikesrvm_path'/dist/'$build_config'_x86_64_m32-linux' $kit_upload/$build_path
}

# build_jikesrvm 'jikesrvm_path' 'plan' 'build_path'
# Env: JAVA_HOME
build_jikesrvm() {
    ensure_env JAVA_HOME

    jikesrvm_path=$1
    build_config=$2
    build_path=$3

    cd $jikesrvm_path

    # build
    bin/buildit localhost $build_config -quick --answer-yes --m32

    # copy to build_path
    cp -r $jikesrvm_path'/dist/'$build_config'_x86_64_m32-linux' $kit_build/$build_path
    # Directly copy to upload. JikesRVM builds are small enough that we can directly upload.
    cp -r $jikesrvm_path'/dist/'$build_config'_x86_64_m32-linux' $kit_upload/$build_path
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

# pgo_build_openjdk_with_mmtk 'binding_path' 'openjdk_path' 'debug_level'
# Build OpenJDK+MMTk using the binding repo's .github/scripts/pgo-build.sh,
# which builds MMTk twice: once instrumented to collect a profile (running
# fop from DaCapo), then again using that profile (PGO). Only supports
# release builds, since pgo-build.sh hardcodes CONF=...-release.
# Env: (optionally) MMTK_PLAN - forwarded as a compile-time cargo feature
pgo_build_openjdk_with_mmtk() {
    binding_path=$1
    openjdk_path=$2
    debug_level=$3

    if [ "$debug_level" != "release" ]; then
        echo "pgo_build_openjdk_with_mmtk only supports release builds (got: $debug_level)"
        exit 1
    fi

    # pgo-build.sh uses paths relative to its cwd (the OpenJDK checkout),
    # assuming the binding repo lives alongside it in a sibling directory
    # named "mmtk-openjdk". Our layout nests openjdk under binding_path/repos,
    # so set up that expected sibling with a symlink instead.
    ln -sfn $(realpath $binding_path) $openjdk_path/../mmtk-openjdk

    # pgo-build.sh hardcodes the llvm-profdata path to a specific pinned Rust
    # toolchain version, which goes stale whenever the binding bumps its
    # rust-toolchain (confirmed: upstream mmtk-openjdk master currently pins
    # 1.83.0 in mmtk/rust-toolchain, but pgo-build.sh still points at 1.71.1).
    # Patch the checked-out copy to match whatever toolchain this checkout
    # actually pins, so the merge step resolves to an installed toolchain.
    rust_toolchain=$(cat $binding_path/mmtk/rust-toolchain)
    sed -i "s#/opt/rust/toolchains/[^/]*/#/opt/rust/toolchains/${rust_toolchain}-x86_64-unknown-linux-gnu/#" $binding_path/.github/scripts/pgo-build.sh

    # pgo-build.sh also hardcodes the DaCapo jar it profiles with (an old
    # Chopin release candidate that no longer exists on disk). Point it at
    # the jar we actually have.
    sed -i "s#/usr/share/benchmarks/dacapo/dacapo-[^ ]*\.jar#$dacapochopin_jar#" $binding_path/.github/scripts/pgo-build.sh

    # CompileThirdPartyHeap.gmk's $(LIB_MMTK) rule is marked FORCE and is
    # invoked from more than one recursive make (main libjvm + the gtest
    # variant); at the default auto-detected parallelism on many-core
    # machines this races (two concurrent `cargo build` + `cp` sequences)
    # and produces "undefined reference" link failures. Confirmed
    # reproducible at -j24 and reliably fixed at JOBS=4 - cap it in
    # pgo-build.sh's "make ... images" invocations.
    sed -i "s#make CONF=#make JOBS=4 CONF=#" $binding_path/.github/scripts/pgo-build.sh

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL
    bash $binding_path/.github/scripts/pgo-build.sh

    # pgo-build.sh only builds the "images" target. Package product-bundles
    # from it, keeping the same profile-use RUSTFLAGS so make doesn't trigger
    # a rebuild of the mmtk library without the PGO profile.
    RUSTFLAGS="-Cprofile-use=/tmp/$USER/pgo-data/merged.profdata -Cllvm-args=-pgo-warn-missing-function" \
        make JOBS=4 product-bundles CONF=$openjdk_build_conf-$DEBUG_LEVEL THIRD_PARTY_HEAP=$PWD/../../openjdk
}

# build_openjdk ’binding_path' 'debug_level' 'build_path'
build_openjdk_with_mmtk() {
    binding_path=$1
    debug_level=$2
    build_path=$3

    openjdk_path=$binding_path/repos/openjdk

    pgo_build_openjdk_with_mmtk $binding_path $openjdk_path $debug_level

    # copy to build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$debug_level $kit_build/$build_path
    # Copy bundles to upload
    mkdir -p $kit_upload/$build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$debug_level/bundles/*_bin.tar.gz $kit_upload/$build_path
}

# build_openjdk ’binding_path' 'plan' 'debug_level' 'build_path'
build_openjdk_with_mmtk_plan() {
    binding_path=$1
    plan=$2
    debug_level=$3
    build_path=$4

    openjdk_path=$binding_path/repos/openjdk

    export MMTK_PLAN=$plan
    pgo_build_openjdk_with_mmtk $binding_path $openjdk_path $debug_level

    # copy to build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$debug_level $kit_build/$build_path
    # Copy bundles to upload
    mkdir -p $kit_upload/$build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$debug_level/bundles/*_bin.tar.gz $kit_upload/$build_path
}

# build_openjdk 'openjdk_path' 'debug_level' 'build_path'
build_openjdk() {
    openjdk_path=$1
    debug_level=$2
    build_path=$3

    cd $openjdk_path
    export DEBUG_LEVEL=$debug_level
    sh configure --disable-warnings-as-errors --with-debug-level=$DEBUG_LEVEL --with-jvm-features=zgc
    make product-bundles CONF=$openjdk_build_conf-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$DEBUG_LEVEL $kit_build/$build_path
    # Copy bundles to upload
    mkdir -p $kit_upload/$build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$DEBUG_LEVEL/bundles/*_bin.tar.gz $kit_upload/$build_path
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
    make product-bundles CONF=$openjdk_build_conf-$DEBUG_LEVEL

    # copy to build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$DEBUG_LEVEL $kit_build/$build_path
    # Copy bundles to upload
    mkdir -p $kit_upload/$build_path
    cp -r $openjdk_path/build/$openjdk_build_conf-$DEBUG_LEVEL/bundles/*_bin.tar.gz $kit_upload/$build_path
}

# build_probes
# Build the anupli/probes submodule: probes.jar/probes-java6.jar (built by
# the submodule's own Makefile using its own hardcoded JAVA8_HOME/JAVA6_HOME,
# so this works regardless of ambient JAVA_HOME - e.g. JikesRVM's Java 6),
# and the native RustMMTk/RustMMTk32/USDT probe libraries.
build_probes() {
    cd $kit_root/probes
    # The submodule defaults DACAPOCHOPINJAR to the base 23.11 release; we use MR2.
    make DACAPOCHOPINJAR=$dacapochopin_jar
}

# build_openjdk_probe
# Build OpenJDKProbe (kept in ci-perf-kit itself, next to the anupli/probes
# submodule, since it isn't part of that submodule) - a JMX-based probe for
# stock (non-MMTk) OpenJDK runs, so only relevant for OpenJDK, not JikesRVM.
# Needs a JAVA_HOME whose javac can read probes.jar's class files (built
# under Java 8 by build_probes above) - i.e. Java 8 or newer. JikesRVM's
# JAVA_HOME is Java 6, which can't, so jikesrvm-history-run.sh must not call
# this (confirmed: it fails with "class file has wrong version 52.0, should
# be 50.0" if it does).
# Env: JAVA_HOME
build_openjdk_probe() {
    ensure_env JAVA_HOME

    cd $kit_root/openjdk-probe
    make
}

# write_commit_info 'output_file' 'binding_name' 'binding_path' ['mmtk_core_path']
# Records which binding (e.g. mmtk-openjdk, mmtk-jikesrvm) and, if given,
# mmtk-core commit a build was built from, as YAML, so a script saving a
# run's results can copy it alongside that run's logs (see
# openjdk-run-plan.sh, jikesrvm-history-run.sh).
write_commit_info() {
    output_file=$1
    binding_name=$2
    binding_path=$3
    mmtk_core_path=$4

    echo "$binding_name: $(git -C $binding_path rev-parse HEAD)" > $output_file
    if [ -n "$mmtk_core_path" ]; then
        echo "mmtk-core: $(git -C $mmtk_core_path rev-parse HEAD)" >> $output_file
    fi
}

# run_benchmarks 'log_dir' 'config' 'heap_modifier' 'invocations'
# heap_modifier=0 means we won't set heap size based on min heap. This is used for NoGC which we set heap size to the maximum instead of a multiple of min heap.
run_benchmarks() {
    outdir=$1
    config=$2
    heap_modifier=$3
    invocations=$4

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
