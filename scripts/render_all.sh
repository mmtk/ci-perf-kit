set -ex

# include common.sh
. $(dirname "$0")/common.sh

# Re-render every plot (OpenJDK + JikesRVM) from whatever is already
# committed to ci-perf-result, without running any benchmarks - e.g. after a
# plot.py change, or to re-point at a different ci-perf-result branch/config
# than the regular per-commit/weekly runs use. OpenJDK and JikesRVM each get
# their own checkout, so they can track different result-repo branches at
# once. See render_all.py for the actual rendering + combined index.html.
#
# render-all.sh 'output_dir' 'openjdk_plot_config' 'jikesrvm_plot_config' 'openjdk_result_repo_branch' 'jikesrvm_result_repo_branch'
#
# Env: RESULT_REPO, RESULT_REPO_ACCESS_TOKEN

output_dir=$(realpath -m $1)
openjdk_plot_config=$2
jikesrvm_plot_config=$3
openjdk_result_repo_branch=$4
jikesrvm_result_repo_branch=$5

openjdk_result_repo_dir=$kit_root/result_repo_openjdk
jikesrvm_result_repo_dir=$kit_root/result_repo_jikesrvm

checkout_result_repo_at $openjdk_result_repo_dir $openjdk_result_repo_branch
checkout_result_repo_at $jikesrvm_result_repo_dir $jikesrvm_result_repo_branch

ensure_empty_dir $output_dir

cd $kit_root
start_venv python-env
pip3 install -r scripts/requirements.txt
python3 scripts/render_all.py $output_dir $openjdk_plot_config $jikesrvm_plot_config $openjdk_result_repo_dir $jikesrvm_result_repo_dir
