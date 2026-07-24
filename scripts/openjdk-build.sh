set -ex

# include common.sh
. $(dirname "$0")/common.sh

# openjdk_binding: path to a checked-out OpenJDK MMTk binding (e.g. mmtk-openjdk),
# with the OpenJDK source under $openjdk_binding/repos/openjdk.
openjdk_binding=$(realpath $1)

ensure_empty_dir $kit_build
ensure_empty_dir $kit_upload

# Build probes (needed on the classpath when running benchmarks below)
build_probes

# Build OpenJDK+MMTk. The result is left at $kit_build/jdk-mmtk (and
# bundled at $kit_upload/jdk-mmtk) for openjdk-run-plan.sh to run against.
build_openjdk_with_mmtk $openjdk_binding release jdk-mmtk
