set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Regenerate the OpenJDK performance-history report from whatever plans are
# currently committed to the result repo. Call this after one or more
# openjdk-run-plan.sh invocations to refresh the report/plot with their
# latest results.
#
# openjdk-report.sh 'output_dir' ['plan_name']
#
# If plan_name is given, only that one plan's graph is (re)generated - the
# rest of the plans' existing graphs are left untouched in output_dir (and,
# since the deploy step publishes with keep_files: true, on the gh-pages
# branch too). Omit it to regenerate every plan's graph, as before.

output_dir=$(realpath -m $1)
plan_name=$2

checkout_result_repo

ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir $plan_name
