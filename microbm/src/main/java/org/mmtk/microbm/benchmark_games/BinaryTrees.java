/**
 * The Computer Language Benchmarks Game
 * https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
 *
 * based on Jarkko Miettinen's Java program
 * contributed by Tristan Dupont
 * *reset*
 */
package org.mmtk.microbm.benchmark_games;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.Benchmark;
import org.openjdk.jmh.annotations.BenchmarkMode;
import org.openjdk.jmh.annotations.Level;
import org.openjdk.jmh.annotations.Mode;
import org.openjdk.jmh.annotations.Param;
import org.openjdk.jmh.annotations.State;
import org.openjdk.jmh.annotations.Scope;
import org.openjdk.jmh.annotations.Setup;

@State(Scope.Thread)
@BenchmarkMode(Mode.AverageTime)
public class BinaryTrees {
    @State(Scope.Benchmark)
    public static class BenchmarkState {
        private static final int MIN_DEPTH = 4;
    }
    
    @Param({"21"})
    private int depth;

    @Benchmark
    public void run() throws InterruptedException {
        int n = depth;
        final ExecutorService executors = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
        
        final int maxDepth = n < (BenchmarkState.MIN_DEPTH + 2) ? BenchmarkState.MIN_DEPTH + 2 : n;
        final int stretchDepth = maxDepth + 1;

        // System.out.println("stretch tree of depth " + stretchDepth + "\t check: " 
        // + bottomUpTree( stretchDepth).itemCheck());

        final TreeNode longLivedTree = bottomUpTree(maxDepth);

        final String[] results = new String[(maxDepth - BenchmarkState.MIN_DEPTH) / 2 + 1];

        for (int d = BenchmarkState.MIN_DEPTH; d <= maxDepth; d += 2) {
            final int depth = d;
            executors.execute(() -> {
                int check = 0;

                final int iterations = 1 << (maxDepth - depth + BenchmarkState.MIN_DEPTH);
                for (int i = 1; i <= iterations; ++i) {
                    final TreeNode treeNode1 = bottomUpTree(depth);
                    check += treeNode1.itemCheck();
                }
                results[(depth - BenchmarkState.MIN_DEPTH) / 2] = 
                iterations + "\t trees of depth " + depth + "\t check: " + check;
            });
        }

        executors.shutdown();
        executors.awaitTermination(120L, TimeUnit.SECONDS);

        // for (final String str : results) {
        //     System.out.println(str);
        // }

        // System.out.println("long lived tree of depth " + maxDepth + 
        //     "\t check: " + longLivedTree.itemCheck());
    }

    private static TreeNode bottomUpTree(final int depth) {
        if (0 < depth) {
            return new TreeNode(bottomUpTree(depth - 1), bottomUpTree(depth - 1));
        }
        return new TreeNode();
    }

    private static final class TreeNode {
        private final TreeNode left;
        private final TreeNode right;

        private TreeNode(final TreeNode left, final TreeNode right) {
            this.left = left;
            this.right = right;
        }

        private TreeNode() {
            this(null, null);
        }

        private int itemCheck() {
            // if necessary deallocate here
            if (null == left) {
                return 1;
            }
            return 1 + left.itemCheck() + right.itemCheck();
        }

    }

}
