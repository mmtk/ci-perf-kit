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

# Build probes
ensure_env JAVA_HOME
cd $kit_root/probes/openjdk
make
cd $kit_root/probes/rust_mmtk
make

# Build
cd $openjdk

# Normal MMTk build
build_openjdk_with_mmtk $openjdk_binding release $kit_build/jdk-mmtk

# Special MMTk builds
build_openjdk_with_mmtk_plan $openjdk_binding nogc_lock_free release $kit_build/jdk-mmtk-lock-free-nogc
build_openjdk_with_mmtk_plan $openjdk_binding nogc_no_zeroing release $kit_build/jdk-mmtk-no-zeroing-nogc

# Stock build
build_openjdk $openjdk release $kit_build/jdk-stock

# Run
mu_run_id=$(run_benchmarks $log_dir $kit_root/configs/running-openjdk-mutator.yml 0 $history_invocations)
# Save result
mkdir -p $result_repo_dir/mutator
cp -r $log_dir/$mu_run_id $result_repo_dir/mutator

# Commit result - comment out the following for testing if you dont want to commit the result
commit_result_repo 'Mutator(OpenJDK) Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/mutator_report.py $result_repo_dir/mutator $output_dir