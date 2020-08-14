set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding=$(realpath $1)
output_dir=$(realpath $2)
openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk

ensure_empty_dir $kit_build
checkout_result_repo

# Build probes
cd $kit_root/probes/openjdk
make
cd $kit_root/probes/rust_mmtk
make

# Build
cd $openjdk

# NoGC
build_openjdk_with_mmtk $openjdk_binding nogc release $kit_build/jdk-mmtk-nogc
# Lock free NoGC
build_openjdk_with_mmtk $openjdk_binding nogc_lock_free release $kit_build/jdk-mmtk-lock-free-nogc
# No zeroing NoGC
build_openjdk_with_mmtk $openjdk_binding nogc_no_zeroing release $kit_build/jdk-mmtk-no-zeroing-nogc
# SemiSpace
build_openjdk_with_mmtk $openjdk_binding semispace release $kit_build/jdk-mmtk-semispace
# Stock OpenJDK
build_openjdk $openjdk_binding/repos/openjdk release $kit_build/jdk-stock
# Symlink
ln -s $kit_build/jdk-stock $kit_build/jdk-epsilon
ln -s $kit_build/jdk-stock $kit_build/jdk-g1

# Run
mu_run_id=$(run_benchmarks $kit_root/configs/RunConfig-OpenJDK-Mutator-History.pm)
# Save result
mkdir -p $result_repo_dir/mutator
cp -r $kit_root/running/results/log/$mu_run_id $result_repo_dir/mutator

# Commit result - comment out the following for testing if you dont want to commit the result
commit_result_repo 'Mutator(OpenJDK) Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/mutator_report.py $result_repo_dir/mutator $output_dir