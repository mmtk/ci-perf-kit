import os
import sys
import history_report
import index_gen

# Re-render every OpenJDK + JikesRVM plot from whatever is already committed
# in each result-repo checkout, and regenerate a single index.html covering
# both. Doesn't run any benchmarks or touch the result repos itself - see
# render-all.sh, which does those checkouts (each runtime can point at a
# different ci-perf-result branch) before calling this.
#
# Usage: python render_all.py <output_dir> <openjdk_plot_config> <jikesrvm_plot_config> <openjdk_result_repo_dir> <jikesrvm_result_repo_dir>
#
# openjdk_plot_config/jikesrvm_plot_config are filenames under configs/ (e.g.
# openjdk-plot.yml) - passed through to index_gen.generate_index as well, so
# the index lists exactly the plans these two configs (which may not be the
# usual defaults) declare, not ci-perf-kit's hardcoded default pair.

if len(sys.argv) != 6:
    print("Usage: python render_all.py <output_dir> <openjdk_plot_config> <jikesrvm_plot_config> <openjdk_result_repo_dir> <jikesrvm_result_repo_dir>")
    sys.exit(1)

output_dir = sys.argv[1]
openjdk_plot_config = sys.argv[2]
jikesrvm_plot_config = sys.argv[3]
openjdk_result_repo_dir = sys.argv[4]
jikesrvm_result_repo_dir = sys.argv[5]

history_report.render_plans(
    os.path.join("configs", openjdk_plot_config),
    os.path.join(openjdk_result_repo_dir, "openjdk"),
    os.path.join(openjdk_result_repo_dir, "openjdk_stock"),
    output_dir,
)
history_report.render_plans(
    os.path.join("configs", jikesrvm_plot_config),
    os.path.join(jikesrvm_result_repo_dir, "jikesrvm"),
    os.path.join(jikesrvm_result_repo_dir, "jikesrvm_stock"),
    output_dir,
)

index_gen.generate_index(output_dir, [openjdk_plot_config, jikesrvm_plot_config])
print("Rendered all plots into %s" % output_dir)
