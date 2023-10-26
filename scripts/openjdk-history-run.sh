set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding=$(realpath $1)
output_dir=$(realpath -m $2)
openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk

ensure_empty_dir $kit_build
checkout_result_repo

# Build
build_openjdk_with_mmtk $openjdk_binding release $kit_build/jdk-mmtk

run_exp() {
    plan=$1
    config=$2
    heap_modifier=$3

    # Run
    run_id=$(run_benchmarks $log_dir $kit_root/configs/$config $heap_modifier)
    # Save result
    mkdir -p $result_repo_dir/openjdk/$plan
    cp -r $log_dir/$run_id $result_repo_dir/openjdk/$plan
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

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
