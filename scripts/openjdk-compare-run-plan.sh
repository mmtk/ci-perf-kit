set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Run a single plan's trunk-vs-branch OpenJDK comparison, generate a
# comparison table and per-metric plots (see compare_plot.py), then save the
# result. Assumes both runtimes referenced by $config already exist under
# $kit_build - i.e. openjdk-build.sh has already been run twice, once with
# build_path=jdk-mmtk-trunk and once with build_path=jdk-mmtk-branch (see
# running-openjdk-*-compare.yml, which reference exactly those two runtime
# names).

# plan_name: result dir name under result_repo/openjdk/pr-<pr_number>/ (e.g. stickyimmix)
plan_name=$1
# config: running-ng config filename under configs/ (e.g. running-openjdk-stickyimmix-compare.yml)
config=$2
# heap_modifier: passed straight to run_benchmarks
heap_modifier=$3
# pr_number: the mmtk-core pull request this comparison is for
pr_number=$4

ensure_empty_dir $log_dir
checkout_result_repo

# Run - the compare config runs both jdk-mmtk-trunk and jdk-mmtk-branch as
# part of the same running-ng invocation, so this produces one run_id
# containing both sides' logs together.
run_id=$(run_benchmarks $log_dir $kit_root/configs/$config $heap_modifier $compare_invocations)

# Carry both sides' commit info into this run's log folder, so it's clear
# which mmtk-core/mmtk-openjdk commits were compared, without needing to
# cross-reference the workflow run that produced it.
for side in trunk branch; do
    commit_info=$kit_build/jdk-mmtk-$side/commit-info.yml
    if [ -f "$commit_info" ]; then
        cp $commit_info $log_dir/$run_id/commit-info-$side.yml
    fi
done

# Generate the comparison table (report.md) and one normalized bar chart per
# metric (plots/*.png), written straight into this run's own log folder so
# they get pushed to the result repo alongside the raw logs by the copy
# below - no separate publishing step needed.
start_venv python-env
pip3 install -r scripts/requirements.txt
python $kit_root/scripts/compare_plot.py $log_dir/$run_id $plan_name jdk-mmtk-trunk jdk-mmtk-branch $compare_invocations $log_dir/$run_id $kit_root/configs/openjdk-plot.yml
leave_venv

# Copy the report out to a fixed path and record the run id in its own file,
# so the calling workflow can pick both up regardless of run_id's value
# without having to parse this script's own stdout (which also carries the
# venv/pip/set-x noise above).
cp $log_dir/$run_id/report.md $kit_root/report.md
echo $run_id > $kit_root/run_id.txt

# Save result. The path embeds the PR number and this run's id, so results
# from repeated/different runs of the same plan on the same PR don't
# collide or overwrite each other.
RESULT_DIR=$result_repo_dir/openjdk/pr-$pr_number/$plan_name
mkdir -p $RESULT_DIR
cp -r $log_dir/$run_id $RESULT_DIR

# Commit result.
commit_result_repo 'OpenJDK compare PR #'$pr_number' ('$plan_name'): '$run_id
