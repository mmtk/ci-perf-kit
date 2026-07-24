set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Regenerate the OpenJDK performance-history report from whatever plans are
# currently committed to the result repo. Independent of which (if any) plan
# was just run - call this after one or more openjdk-run-plan.sh invocations
# to refresh the report/plot with their latest results.

output_dir=$(realpath -m $1)

checkout_result_repo

ensure_empty_dir $output_dir
cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/history_report.py configs/openjdk-plot.yml $result_repo_dir/openjdk $result_repo_dir/openjdk_stock $output_dir
