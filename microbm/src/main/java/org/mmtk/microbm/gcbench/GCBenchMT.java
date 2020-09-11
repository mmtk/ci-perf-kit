package org.mmtk.microbm.gcbench;

// GCBenchMT.java
// Jeremy Singer
// 20 Feb 14

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.openjdk.jmh.annotations.*;

import java.util.ArrayList;
import java.util.Stack;
import java.util.Random;

/**
 * a multi-threaded implementation of Java GCBench,
 * for testing GC performance on NUMA machines
 */
@State(Scope.Benchmark)
@BenchmarkMode(Mode.AverageTime)
public class GCBenchMT {
  /**
   * pointers to long-lived data structures,
   * only for -remoteMem flag.
   * (global array across all threads)
   */
  public Node [] longLivedTrees;

  public static Node longLivedPointer0;
  public static Node longLivedPointer1;
  public static Node longLivedPointer2;
  public static Node longLivedPointer3;

  /**
   * if true, we fill the longLivedTrees data
   * structure with node trees that have
   * cross-NUMA-region pointers.
   * set using -remoteMem command line option.
   */
  private boolean enableRemoteMem;
  
  /**
   * number of concurrent GC worker threads
   * to run.
   * set using -numThreads N command line option.
   */
  private int numThreads;

  public int getNumThreads() {
    return this.numThreads;
  }

  /**
   * pool (per thread) of Node objects to use
   * when constructing data for
   * longLivedTrees - use for remoteMem
   */
  private ArrayList<Stack<Node>> pools;

  /**
   * distance between consecutively sampled
   * pools - make this larger to get more cross-NUMA
   * region pointers
   */
  public static final int POOL_STRIDE = 9;

  /**
   * main constructor
   */
  public GCBenchMT() {
    this.numThreads = Runtime.getRuntime().availableProcessors();
    this.enableRemoteMem = true;
    // init LongLivedTrees array if necessary
    // and Node pools
    if (enableRemoteMem) {
      longLivedTrees = new Node[numThreads];
      pools = new ArrayList<Stack<Node>>();
      for (int i=0; i<numThreads; i++) {
        pools.add(i, new Stack<Node>());
      }
    }
    else {
      longLivedTrees = null;
      pools = null;
    }
  }

  /**
   * sets up global data structures and 
   * orchestrates execution of parallel
   * worker threads.
   * Three phases:
   * 1) LongLivedRunner threads create pools
   *    of thread-local Node objects
   * 2) generate global trees with cross-NUMA-region
   *    pointers
   * 3) GCBenchRunner threads exercise the GC
   *    with thread-local short- and long-lived 
   *    data structures.
   * Phases 1 and 2 only enabled for remoteMem
   * option. Phase 3 always executes.
   */
  public void start() {    
        if (enableRemoteMem) {
        // phase 1
        // System.out.println("Allocating Node object pools");
        LongLivedRunner [] llRunners = new LongLivedRunner[numThreads];
        for (int i=0; i<numThreads; i++) {
            // allocate single nodes into thread-local pools
            LongLivedRunner l = new LongLivedRunner(i, pools.get(i));
            llRunners[i] = l;
        }

        ExecutorService executor = Executors.newFixedThreadPool(numThreads);
        for (LongLivedRunner l : llRunners) {
            executor.execute(l);
        }

        executor.shutdown();
        // Wait until all threads finish
        try {
            // Wait a while for existing tasks to terminate
            if (!executor.awaitTermination(60, TimeUnit.SECONDS)) {
            executor.shutdownNow(); // Cancel currently executing tasks
            // Wait a while for tasks to respond to being cancelled
            if (!executor.awaitTermination(60, TimeUnit.SECONDS))
                System.err.println("Pool did not terminate");
            }
        } catch (InterruptedException ie) {
            // (Re-)Cancel if current thread also interrupted
            executor.shutdownNow();
            // Preserve interrupt status
            Thread.currentThread().interrupt();
        }
        // System.out.println("Finished allocating Node object pools");

        // phase 2
        // System.out.println("About to shuffle pointers between thread-local data structures...");

        // iterate over each depth of tree
        // at each depth, make all nodes in trees[i] point to nodes in trees[i+1]
        for (int i=0; i<numThreads; i++) {
            Node remoteTree = MakeRemoteTree(GCBenchST.kLongLivedTreeDepth, i);
            longLivedTrees[i] = remoteTree;
        }

        // System.out.println("Finished shuffling pointers between thread-local data structures.");

        
        } // if (enableRemoteMem)

        // phase 3
        GCBenchRunner [] runners= new GCBenchRunner[numThreads];
        for (int i=0; i<numThreads; i++) {
        GCBenchRunner r = new GCBenchRunner(i, !enableRemoteMem, this);
        runners[i] = r;
        }

        ExecutorService executor = Executors.newFixedThreadPool(numThreads);
        for (GCBenchRunner r : runners) {
        executor.execute(r);
        }

        executor.shutdown();
        // Wait until all threads finish
        try {
        // Wait a while for existing tasks to terminate
        if (!executor.awaitTermination(60, TimeUnit.SECONDS)) {
            executor.shutdownNow(); // Cancel currently executing tasks
            // Wait a while for tasks to respond to being cancelled
            if (!executor.awaitTermination(60, TimeUnit.SECONDS))
            System.err.println("Pool did not terminate");
        }
        } catch (InterruptedException ie) {
        // (Re-)Cancel if current thread also interrupted
        executor.shutdownNow();
        // Preserve interrupt status
        Thread.currentThread().interrupt();
        }
        // System.out.println("[harness] Finished all threads");

        if (this.enableRemoteMem) {
        Random rng = new Random();
        int r = rng.nextInt(numThreads);
        if (longLivedTrees[r] == null)
            System.err.println("Failed");
        // fake reference to longLivedTrees
        // to keep them from being optimized away
        }

    }

    /**
     * builds a tree bottom-up, with
     * nodes at each level from a different 
     * thread allocation pool to induce lots
     * of cross-NUMA-region pointers
     */
    public Node MakeRemoteTree(int iDepth, int currentPool) {
        Node n = getNewNodeFromPool(currentPool);
        if (iDepth>0) {
        n.left = MakeRemoteTree(iDepth-1, nextPool(currentPool));
        n.right = MakeRemoteTree(iDepth-1, nextPool(currentPool));
        }
        return n;
    }

    /**
     * fetch a pre-allocated Node
     * instance from the specified
     * thread-local pool
     */
    public Node getNewNodeFromPool(int pool) {
        // return node from the indexed pool (list)
        return pools.get(pool).pop();
    }

    /**
     * which pool should we use for the next level of
     * allocation depth? (rotate round all pools in 
     * round-robin order)
     */
    public int nextPool(int pool) {
        return (pool+POOL_STRIDE)%this.numThreads;
    }

    /**
     * entry point for GCBenchMT - parses
     * command line options then instantiates
     * object of this type.
     */
    @Benchmark
    public void run() {
        GCBenchMT gcb = new GCBenchMT();
        gcb.start();
    } // main()

    /**
     * print version of program to stderr
     * (invoke with -version option on CLI)
     */
    public static void printVersion() {
        
    }

    public static class GCBenchRunner implements Runnable {

        /**
         * unique id number for this GCBenchRunner thread
         */
        private int id;
    
        /**
         * should this thread allocate some
         * long-lived data locally?
         */
        private boolean localLongLivedData;
    
        /**
         * harness for multi-threaded 
         * GCBench execution
         */
        private GCBenchMT harness;
    
        public GCBenchRunner(int id) {
        this(id, true, null);
        }
    
        public GCBenchRunner(int id, boolean localLongLivedData, GCBenchMT harness) {
        this.id = id;
        this.localLongLivedData = localLongLivedData;
        this.harness = harness;
        }
    
        public static final int kStretchTreeDepth    = 18;	// about 16Mb
        public static final int kLongLivedTreeDepth  = 16;  // about 4Mb
        public static final int kArraySize  = 500000;  // about 4Mb
        public static final int kMinTreeDepth = 4;
        public static final int kMaxTreeDepth = 16;
    
            @Override
        public void run() {
            Node	root;
            Node	longLivedTree = null; // for local long-lived data
            Node	tempTree;
            long	tStart, tFinish;
            long	tElapsed;
                    double [] array = null; // for local long-lived data
    
            output("Garbage Collector Test");
            output(
                " Stretching memory with a binary tree of depth "
                + kStretchTreeDepth);
            GCBenchST.PrintDiagnostics();
            tStart = System.currentTimeMillis();
    
            // Stretch the memory space quickly
            tempTree = GCBenchST.MakeTree(kStretchTreeDepth);
            tempTree = null;
    
                    if (this.localLongLivedData) {
                        // Create a long lived object
                        output(
                            " Creating a long-lived binary tree of depth " +
                            kLongLivedTreeDepth);
                        longLivedTree = new Node();
                        GCBenchST.Populate(kLongLivedTreeDepth, longLivedTree);
                        
                        // Create long-lived array, filling half of it
                        output(
                            " Creating a long-lived array of "
                            + kArraySize + " doubles");
                        array = new double[kArraySize];
                        for (int i = 0; i < kArraySize/2; ++i) {
                        array[i] = 1.0/i;
                        }
                    }
                    
            GCBenchST.PrintDiagnostics();
                    
                    // now allocate local short-lived data
                    
            for (int d = kMinTreeDepth; d <= kMaxTreeDepth; d += 2) {
                        GCBenchST.TimeConstruction(d);
    
                        // @jsinger
                        // shuffle long-lived pointers here
                        // (from harness-allocated data - change its
                        // static pointers)
                        Random rng = new Random();
                        int r0 = rng.nextInt(harness.getNumThreads());
                        int r1 = rng.nextInt(harness.getNumThreads());
                        int r2 = rng.nextInt(harness.getNumThreads());
                        int r3 = rng.nextInt(harness.getNumThreads());
                        GCBenchMT.longLivedPointer0 = harness.longLivedTrees[r0];
                        GCBenchMT.longLivedPointer1 = harness.longLivedTrees[r1];
                        GCBenchMT.longLivedPointer2 = harness.longLivedTrees[r2];
                        GCBenchMT.longLivedPointer3 = harness.longLivedTrees[r3];
            }
                    
                    
                    if (this.localLongLivedData) {
                        if (longLivedTree == null || array[1000] != 1.0/1000)
                        output("Failed");
                        // fake reference to LongLivedTree
                        // and array
                        // to keep them from being optimized away
                    }
    
            tFinish = System.currentTimeMillis();
            tElapsed = tFinish-tStart;
            GCBenchST.PrintDiagnostics();
            output("Completed in " + tElapsed + "ms.");
        }
    
    
        public void output(String s) {
            // System.out.printf("[%d] %s\n", id, s);
        }
    } // class GCBenchRunner

    public class LongLivedRunner implements Runnable {

    /**
     * unique id for this thread
     */
    private int id;

    /** 
     * pool where allocated Nodes are stored
     */
    private Stack<Node> pool;
    
    /**
     * constructor
     */
    public LongLivedRunner(int id, Stack<Node> pool) {
        this.id = id;
        this.pool = pool;
    }

    @Override
    public void run() {
        output("allocating local nodes");
        int numNodes = GCBenchST.TreeSize(GCBenchST.kLongLivedTreeDepth);
        for (int i=0; i<numNodes; i++) {
        pool.push(new Node());
        }
    }
        

    public void output(String s) {
        // System.out.printf("[%d] %s\n", id, s);
    }
    } // class LongLivedRunner
}