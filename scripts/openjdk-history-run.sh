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

# Build
cd $openjdk

# NoGC
build_openjdk_with_mmtk $openjdk_binding nogc release $kit_build/jdk-mmtk-nogc
# Run For NoGC
nogc_run_id=$(run_benchmarks $kit_root/configs/RunConfig-OpenJDK-NoGC-Complete.pm)
# Save result
mkdir -p $result_repo_dir/openjdk/nogc
cp -r $kit_root/running/results/log/$nogc_run_id $result_repo_dir/openjdk/nogc

# SemiSpace
build_openjdk_with_mmtk $openjdk_binding semispace release $kit_build/jdk-mmtk-semispace
# Run For SemiSpace
ss_run_id=$(run_benchmarks $kit_root/configs/RunConfig-OpenJDK-SemiSpace-Complete.pm)
# Save result
mkdir -p $result_repo_dir/openjdk/semispace
cp -r $kit_root/running/results/log/$ss_run_id $result_repo_dir/openjdk/semispace

# GenCopy
build_openjdk_with_mmtk $openjdk_binding gencopy release $kit_build/jdk-mmtk-gencopy
# Run For GenCopy
gencopy_run_id=$(run_benchmarks $kit_root/configs/RunConfig-OpenJDK-GenCopy-Complete.pm)
# Save result
mkdir -p $result_repo_dir/openjdk/gencopy
cp -r $kit_root/running/results/log/$gencopy_run_id $result_repo_dir/openjdk/gencopy

# Commit result
commit_result_repo 'OpenJDK Binding: '$openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py $result_repo_dir/openjdk $output_dir openjdk
