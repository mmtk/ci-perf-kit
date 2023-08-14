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

run_exp() {
    plan=$1
    config=$2

    # Build
    build_openjdk_with_mmtk $openjdk_binding $plan release $kit_build/jdk-mmtk-$plan
    # Run
    run_id=$(run_benchmarks $kit_root/configs/$config)
    # Save result
    mkdir -p $result_repo_dir/openjdk/$plan
    cp -r $kit_root/running/results/log/$run_id $result_repo_dir/openjdk/$plan
}

# Build
cd $openjdk

# NoGC
run_exp nogc RunConfig-OpenJDK-NoGC-Complete.pm

# SemiSpace
run_exp semispace RunConfig-OpenJDK-SemiSpace-Complete.pm

# GenCopy
run_exp gencopy RunConfig-OpenJDK-GenCopy-Complete.pm

# Immix
run_exp immix RunConfig-OpenJDK-Immix-Complete.pm

# GenImmix
run_exp genimmix RunConfig-OpenJDK-GenImmix-Complete.pm

# StickyImmix
run_exp stickyimmix RunConfig-OpenJDK-StickyImmix-Complete.pm

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
