set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Thin wrapper over openjdk-build.sh and openjdk-run-plan.sh for local/manual
# runs. GitHub workflows that want to parallelize per-plan should call those
# two scripts directly instead.

openjdk_binding_latest=$(realpath $1)
openjdk_binding_canary_build=$(realpath $2)
output_dir=$(realpath -m $3)
# openjdk_rev is used for the commit message. We use the revision ID of the latest version.
openjdk_rev=$(git -C $openjdk_binding_latest rev-parse HEAD)

# Build
bash $kit_script/openjdk-build.sh $openjdk_binding_latest

# Copy the canary build into place. running-openjdk-canary-complete.yml
# expects a prebuilt runtime at build/jdk-mmtk-canary.
cp -r $openjdk_binding_canary_build $kit_build/jdk-mmtk-canary

# Run one plan at a time, each saving and committing its own result.
bash $kit_script/openjdk-run-plan.sh nogc running-openjdk-nogc-complete.yml 0 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh semispace running-openjdk-semispace-complete.yml 6 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh gencopy running-openjdk-gencopy-complete.yml 6 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh immix running-openjdk-immix-complete.yml 6 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh genimmix running-openjdk-genimmix-complete.yml 6 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh stickyimmix running-openjdk-stickyimmix-complete.yml 6 $openjdk_rev

bash $kit_script/openjdk-run-plan.sh marksweep running-openjdk-marksweep-complete.yml 6 $openjdk_rev

# GenImmix using the canary version.
# If the performance of the canary version changed,
# it means there is an environment change that impacts the performance.
bash $kit_script/openjdk-run-plan.sh canary running-openjdk-canary-complete.yml 6 $openjdk_rev

# plot result
ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
