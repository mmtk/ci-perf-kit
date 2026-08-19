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
# build_path: optional name for the build dir under $kit_build/ (and
# $kit_upload/). Defaults to 'jdk-mmtk' (the name openjdk-run-plan.sh and
# every running-openjdk-*-complete.yml config expect). Callers that need
# more than one build to coexist under the same $kit_build - e.g. a
# trunk/branch pair for PR comparison, restored from two separate caches -
# pass distinct names here (see running-openjdk-*-compare.yml, which
# reference 'jdk-mmtk-trunk'/'jdk-mmtk-branch' explicitly).
build_path=${3:-jdk-mmtk}

ensure_empty_dir $kit_build
ensure_empty_dir $kit_upload

# Build probes (needed on the classpath when running benchmarks below)
build_probes
build_openjdk_probe

# Build OpenJDK+MMTk. The result is left at $kit_build/$build_path (and
# bundled at $kit_upload/$build_path) for openjdk-run-plan.sh to run against.
build_openjdk_with_mmtk $openjdk_binding release $build_path

# Record which commits went into this build, so openjdk-run-plan.sh can
# carry it into each run's log folder.
write_commit_info $kit_build/$build_path/commit-info.yml mmtk-openjdk $openjdk_binding $mmtk_core
