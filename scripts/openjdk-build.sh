set -ex

# include common.sh
. $(dirname "$0")/common.sh

# openjdk_binding: path to a checked-out OpenJDK MMTk binding (e.g. mmtk-openjdk),
# with the OpenJDK source under $openjdk_binding/repos/openjdk.
openjdk_binding=$(realpath $1)
# mmtk_core: optional path to a checked-out mmtk-core, if the binding was
# built against a specific/local mmtk-core commit (e.g. via
# ci-replace-mmtk-dep.sh). Only used to record the commit below; the build
# itself already resolved whatever mmtk-openjdk/mmtk/Cargo.toml points at.
if [ -n "$2" ]; then
    mmtk_core=$(realpath $2)
else
    mmtk_core=
fi

ensure_empty_dir $kit_build
ensure_empty_dir $kit_upload

# Build probes (needed on the classpath when running benchmarks below)
build_probes

# Build OpenJDK+MMTk. The result is left at $kit_build/jdk-mmtk (and
# bundled at $kit_upload/jdk-mmtk) for openjdk-run-plan.sh to run against.
build_openjdk_with_mmtk $openjdk_binding release jdk-mmtk

# Record which commits went into this build, so openjdk-run-plan.sh can
# carry it into each run's log folder.
write_commit_info $kit_build/jdk-mmtk/commit-info.yml mmtk-openjdk $openjdk_binding $mmtk_core
