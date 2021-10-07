set -ex

# include common.sh
. $(dirname "$0")/common.sh

openjdk_binding_trunk=$(realpath $1)
mmtk_core_trunk=$(realpath $2)
openjdk_binding_branch=$(realpath $3)
mmtk_core_branch=$(realpath $4)
output_file=$(realpath -m $5)

openjdk_trunk_rev=$(git -C $openjdk_binding_trunk rev-parse HEAD)
mmtk_trunk_rev=$(git -C $mmtk_core_trunk rev-parse HEAD)
openjdk_branch_rev=$(git -C $openjdk_binding_branch rev-parse HEAD)
mmtk_branch_rev=$(git -C $mmtk_core_branch rev-parse HEAD)

# OpenJDK root
openjdk_trunk=$openjdk_binding_trunk/repos/openjdk
openjdk_branch=$openjdk_binding_branch/repos/openjdk

# --- Build ----

# Edit openjdk binding Cargo.toml to use local path for mmtk core - note: this makes this script not repeatable
openjdk_binding_use_local_mmtk $openjdk_binding_trunk
if [ "$openjdk_binding_branch" != "$openjdk_binding_trunk" ]; then
    openjdk_binding_use_local_mmtk $openjdk_binding_branch
fi

ensure_empty_dir $kit_build

# Build for trunk
ensure_empty_dir $openjdk_binding_trunk/repos/mmtk-core
cp -r $mmtk_core_trunk/* $openjdk_binding_trunk/repos/mmtk-core/
build_openjdk_with_mmtk $openjdk_binding_trunk release $kit_build/jdk-mmtk-trunk

# Build for branch
ensure_empty_dir $openjdk_binding_branch/repos/mmtk-core
cp -r $mmtk_core_branch/* $openjdk_binding_branch/repos/mmtk-core/
build_openjdk_with_mmtk $openjdk_binding_branch release $kit_build/jdk-mmtk-branch

# --- Run ---

cd $kit_root

echo "OpenJDK" >> $output_file
echo "====" >> $output_file

echo "* binding_trunk: [$openjdk_trunk_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_trunk_rev)" >> $output_file
echo "* trunk:   [$mmtk_trunk_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_trunk_rev)" >> $output_file
echo "* binding_branch: [$openjdk_branch_rev](https://github.com/mmtk/mmtk-openjdk/commit/$openjdk_branch_rev)" >> $output_file
echo "* branch:  [$mmtk_branch_rev](https://github.com/mmtk/mmtk-core/commit/$mmtk_branch_rev)" >> $output_file

echo "" >> $output_file

ensure_empty_dir $log_dir

# NoGC
nogc_run_id=$(run_benchmarks_custom_heap $log_dir $kit_root/configs-ng/openjdk/compare/nogc.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$nogc_run_id NoGC jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file

# SemiSpace
ss_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/compare/semispace.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$ss_run_id SemiSpace jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file

# GenCopy
gencopy_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/compare/gencopy.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$gencopy_run_id GenCopy jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file

# GenImmix
genimmix_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/compare/genimmix.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$genimmix_run_id GenImmix jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file

# MarkSweep
ms_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/compare/marksweep.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$ms_run_id MarkSweep jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file

# Immix
ix_run_id=$(run_benchmarks $log_dir $kit_root/configs-ng/openjdk/compare/immix.yml $compare_invocations)
python $kit_root/scripts/compare_report.py $log_dir/$ix_run_id Immix jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations >> $output_file