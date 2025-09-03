set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding_latest=$(realpath $1)
openjdk_binding_canary_build=$(realpath $2)
output_dir=$(realpath -m $3)
# openjdk_rev is used for the commit message.  We use the revision ID of the latest version.
openjdk_rev=$(git -C $openjdk_binding_latest rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding_latest/repos/openjdk

ensure_empty_dir $kit_build
ensure_empty_dir $kit_upload
ensure_empty_dir $log_dir
checkout_result_repo

# Build
build_openjdk_with_mmtk $openjdk_binding_latest release jdk-mmtk

# Copy the canary build to the kit build directory.
cp -r $openjdk_binding_canary_build $kit_build/jdk-mmtk-canary

run_exp() {
    dir_name=$1
    config=$2
    heap_modifier=$3
    invocations=$history_invocations

    # Use this when testing the scripts so that tests run faster, albeit producing less accurate results.
    if [ "$OPENJDK_HISTORY_RUN_TEST_FAST" = "1" ]; then
        invocations=1
    fi

    # Run
    run_id=$(run_benchmarks $log_dir $kit_root/configs/$config $heap_modifier $invocations)
    # Save result
    RESULT_DIR=$result_repo_dir/openjdk/$dir_name
    mkdir -p $RESULT_DIR
    cp -r $log_dir/$run_id $RESULT_DIR
}

# Build
cd $openjdk

# NoGC
run_exp nogc running-openjdk-nogc-complete.yml 0

# SemiSpace
run_exp semispace running-openjdk-semispace-complete.yml 6

# GenCopy
run_exp gencopy running-openjdk-gencopy-complete.yml 6

# Immix
run_exp immix running-openjdk-immix-complete.yml 6

# GenImmix
run_exp genimmix running-openjdk-genimmix-complete.yml 6

# StickyImmix
run_exp stickyimmix running-openjdk-stickyimmix-complete.yml 6

# MarkSweep
run_exp marksweep running-openjdk-marksweep-complete.yml 6

# GenImmix using the canary version.
# If the performance of the canary version changed,
# it means there is an environment change that impacts the performance.
run_exp canary running-openjdk-canary-complete.yml 6

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
