set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding=$(realpath $1)
output_dir=$(realpath -m $2)
openjdk_rev=$(git -C $openjdk_binding rev-parse HEAD)

# OpenJDK root
openjdk=$openjdk_binding/repos/openjdk
checkout_result_repo

# Build probes
# cd $kit_root/probes/openjdk
# make
# cd $kit_root/probes/rust_mmtk
# make
cd $kit_root/probes
make

# Build
cd $openjdk

ensure_empty_dir $kit_build
# MMTk
build_openjdk_with_mmtk $openjdk_binding release $kit_build/jdk-mmtk
ln -s $kit_build/jdk-mmtk $kit_build/jdk-mmtk-nogc
ln -s $kit_build/jdk-mmtk $kit_build/jdk-mmtk-semispace
ln -s $kit_build/jdk-mmtk $kit_build/jdk-mmtk-immix
# Lock free NoGC
build_openjdk_with_mmtk_features $openjdk_binding nogc_lock_free release $kit_build/jdk-mmtk-lock-free-nogc
# No zeroing NoGC
build_openjdk_with_mmtk_features $openjdk_binding nogc_no_zeroing release $kit_build/jdk-mmtk-no-zeroing-nogc
# Stock OpenJDK
build_openjdk $openjdk_binding/repos/openjdk release $kit_build/jdk-stock
ln -s $kit_build/jdk-stock $kit_build/jdk-stock-epsilon
ln -s $kit_build/jdk-stock $kit_build/jdk-stock-g1

# Run
mu_run_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/openjdk/mutator/base.yml $history_invocations)
# Save result
mkdir -p $result_repo_dir/mutator
cp -r $log_dir/$mu_run_id $result_repo_dir/mutator

# Commit result - comment out the following for testing if you dont want to commit the result
commit_result_repo 'Mutator(OpenJDK) Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
python3 scripts/mutator_report.py $result_repo_dir/mutator $output_dir
