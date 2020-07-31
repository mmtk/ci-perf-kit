/**
 *   This probe code is from Vishal Singh (tmibvishal@github). 
 *   
 *   It can be accessed from Xi Yang's repo (https://github.com/yangxi/openjdk-wb/) (collaborator access required):
 *   https://github.com/yangxi/openjdk-wb/blob/60502df1a631f40df3a4353f3ee43c1f9d0f4ff9/probes/probe/DacapoBetaProbe.java
 *
 *   Changes:
 *   - removed some debugging outputs
 *   - do not collect statistics for begin()/end() if warmup
 */

package probe;

import java.lang.management.CompilationMXBean;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.MemoryPoolMXBean;
import java.lang.management.MemoryUsage;
import java.lang.management.OperatingSystemMXBean;
import java.util.Date;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

public class OpenJDKProbe implements Probe, Runnable {
    private final OperatingSystemMXBean operatingSystem = ManagementFactory.getOperatingSystemMXBean();
    private final CompilationMXBean jitCompiler = ManagementFactory.getCompilationMXBean();
    private final MemoryMXBean heapMemory = ManagementFactory.getMemoryMXBean();
    private final AtomicInteger starts = new AtomicInteger();
    private volatile MemoryPoolMXBean youngMemoryPool;
    private volatile MemoryPoolMXBean survivorMemoryPool;
    private volatile MemoryPoolMXBean oldMemoryPool;

//    // extra
//    private volatile MemoryPoolMXBean metaspacePool;
//    private volatile MemoryPoolMXBean compressedClassSpacePool;

    private volatile boolean hasMemoryPools;
    private volatile ScheduledFuture<?> memoryPoller;
    private volatile GarbageCollectorMXBean youngCollector;
    private volatile GarbageCollectorMXBean oldCollector;
    private volatile boolean hasCollectors;
    private volatile ScheduledExecutorService scheduler;
    private volatile boolean polling;
    private volatile long lastYoungUsed;
    private volatile long startYoungCollections;
    private volatile long startYoungCollectionsTime;
    private volatile long totalYoungUsed;
    private volatile long lastSurvivorUsed;
    private volatile long totalSurvivorUsed;
    private volatile long lastOldUsed;
    private volatile long startOldCollections;
    private volatile long startOldCollectionsTime;
    private volatile long totalOldUsed;
    private volatile long startTime;
    private volatile long startProcessCPUTime;
    private volatile long startJITCTime;


    public void init() {
        List<MemoryPoolMXBean> memoryPools = ManagementFactory.getMemoryPoolMXBeans();
        for (MemoryPoolMXBean memoryPool : memoryPools) {
            if ("PS Eden Space".equals(memoryPool.getName()) || "Par Eden Space".equals(memoryPool.getName())
                    || "G1 Eden".equals(memoryPool.getName()) || "G1 Eden Space".equals(memoryPool.getName()) || "Eden Space".equals((memoryPool.getName()))) {
                youngMemoryPool = memoryPool;
            } else if ("PS Survivor Space".equals(memoryPool.getName()) || "Par Survivor Space".equals(memoryPool.getName())
                    || "G1 Survivor".equals(memoryPool.getName()) || "G1 Survivor Space".equals(memoryPool.getName()) || "Survivor Space".equals(memoryPool.getName())) {
                survivorMemoryPool = memoryPool;
            } else if ("PS Old Gen".equals(memoryPool.getName()) || "CMS Old Gen".equals(memoryPool.getName())
                    || "G1 Old Gen".equals(memoryPool.getName()) || "Tenured Gen".equals(memoryPool.getName())) {
                oldMemoryPool = memoryPool;
//            } else if ("Metaspace".equals(memoryPool.getName())) {
//                metaspacePool = memoryPool;
//            } else if ("Compressed Class Space".equals(memoryPool.getName())) {
//                compressedClassSpacePool = memoryPool;
            }
        }
        hasMemoryPools = youngMemoryPool != null && survivorMemoryPool != null && oldMemoryPool != null;
        System.out.println("hasMemoryPools" + hasMemoryPools);
        List<GarbageCollectorMXBean> garbageCollectors = ManagementFactory.getGarbageCollectorMXBeans();
        for (GarbageCollectorMXBean garbageCollector : garbageCollectors) {
            if ("PS Scavenge".equals(garbageCollector.getName()) || "ParNew".equals(garbageCollector.getName())
                    || "G1 Young Generation".equals(garbageCollector.getName()) || "Copy".equals(garbageCollector.getName())) {
                // in serial gc we have copy and MarkSweepCompact. I am adding copy in young collector
                youngCollector = garbageCollector;
            } else if ("PS MarkSweep".equals(garbageCollector.getName())
                    || "ConcurrentMarkSweep".equals(garbageCollector.getName())
                    || "G1 Old Generation".equals(garbageCollector.getName()) || "MarkSweepCompact".equals(garbageCollector.getName())) {
                // and adding MarkSweepCompact in old gen
                oldCollector = garbageCollector;
            }
        }
        hasCollectors = youngCollector != null && oldCollector != null;
    }

    public void cleanup() {
        System.out.println("OpenJDKProbe.cleanup()");
    }

    public void begin(String benchmark, int iteration, boolean warmup) {
        System.out.println("\n\n\nOpenJDKProbe.begin(benchmark = " + benchmark + ", iteration = " + iteration + ", warmup = " + warmup + ")");
        if (warmup) 
            return;

        boolean success = startStatistics();
        if (success) {
            System.out.println("OpenJDKProbe: Statistics started successful");
        } else {
            System.err.println("error: OpenJDKProbe: Statistics could not start");
        }
    }

    public void end(String benchmark, int iteration, boolean warmup) {
        System.out.println("OpenJDKProbe.end(benchmark = " + benchmark + ", iteration = " + iteration + ", warmup = " + warmup + ")");
        if (warmup)
            return;

        boolean endedSuccess = stopStatistics(warmup);
        if (endedSuccess) {
            System.out.println("OpenJDKProbe: Statistics ended successful");
        } else {
            System.err.println("error: OpenJDKProbe: Statistics could not end");
        }
    }

    public void report(String benchmark, int iteration, boolean warmup) {
        System.err.println("OpenJDKProbe.report(benchmark = " + benchmark + ", iteration = " + iteration + ", warmup = " + warmup + ")");
    }

    @Override
    public void run() {
        System.out.println("\nOpenJDKProbe.run() " + Thread.currentThread().getName() + ", executing run() method!");
        if (!hasMemoryPools)
            return;

        long young = youngMemoryPool.getUsage().getUsed();
        long survivor = survivorMemoryPool.getUsage().getUsed();
        long old = oldMemoryPool.getUsage().getUsed();
        if (!polling) {
            polling = true;
        } else {
            if (lastYoungUsed <= young) {
                totalYoungUsed += young - lastYoungUsed;
            }
            if (lastSurvivorUsed <= survivor) {
                totalSurvivorUsed += survivor - lastSurvivorUsed;
            }
            if (lastOldUsed <= old) {
                totalOldUsed += old - lastOldUsed;
            } else {
                // May need something more here, like "how much was collected"
            }
        }
        lastYoungUsed = young;
        lastSurvivorUsed = survivor;
        lastOldUsed = old;
    }

    public boolean startStatistics() {
        // Support for multiple nodes requires to ignore start requests after the
        // first
        // but also requires that requests after the first wait until the
        // initialization
        // is completed (otherwise node #2 may start the run while the server is
        // GC'ing)
        synchronized (this) {
            if (starts.incrementAndGet() > 1)
                return false;

            System.gc();
            System.err.println("========================================");
            System.err.println("Statistics Started at " + new Date());
            System.err.println("Operative System: " + operatingSystem.getName() + " " + operatingSystem.getVersion() + " "
                    + operatingSystem.getArch());
            System.err.println("JVM : " + System.getProperty("java.vm.vendor") + " " + System.getProperty("java.vm.name")
                    + " runtime " + System.getProperty("java.vm.version") + " " + System.getProperty("java.runtime.version"));
            System.err.println("Processors: " + operatingSystem.getAvailableProcessors());
            if (operatingSystem instanceof com.sun.management.OperatingSystemMXBean) {
                com.sun.management.OperatingSystemMXBean os = (com.sun.management.OperatingSystemMXBean) operatingSystem;
                long totalMemory = os.getTotalPhysicalMemorySize();
                long freeMemory = os.getFreePhysicalMemorySize();
                System.err.println("System Memory: " + percent(totalMemory - freeMemory, totalMemory) + "% used of "
                        + gibiBytes(totalMemory) + " GiB");
            } else {
                System.err.println("System Memory: N/A");
            }

            MemoryUsage heapMemoryUsage = heapMemory.getHeapMemoryUsage();
            System.err.println("Used Heap Size: " + mebiBytes(heapMemoryUsage.getUsed()) + " MiB");
            System.err.println("Max Heap Size: " + mebiBytes(heapMemoryUsage.getMax()) + " MiB");
            if (hasMemoryPools) {
                long youngGenerationHeap = heapMemoryUsage.getMax() - oldMemoryPool.getUsage().getMax();
                System.err.println("Young Generation Heap Size: " + mebiBytes(youngGenerationHeap) + " MiB");
            } else {
                System.err.println("Young Generation Heap Size: N/A");
            }
            System.err.println("- - - - - - - - - - - - - - - - - - - - ");

            if (hasMemoryPools) {
                lastYoungUsed = youngMemoryPool.getUsage().getUsed();
                lastSurvivorUsed = survivorMemoryPool.getUsage().getUsed();
                lastOldUsed = oldMemoryPool.getUsage().getUsed();
            }

            lastYoungUsed = 0;
            totalSurvivorUsed = 0;
            totalOldUsed = 0;

            // scheduler = Executors.newSingleThreadScheduledExecutor();
            // polling = false;
            // memoryPoller = scheduler.scheduleWithFixedDelay(this, 0, 20, TimeUnit.MILLISECONDS);

            if (hasCollectors) {
                startYoungCollections = youngCollector.getCollectionCount();
                startYoungCollectionsTime = youngCollector.getCollectionTime();
                System.out.println("OpenJDKProbe: Printing startYoungCollectionsTime " + startYoungCollectionsTime);
            }

            if (hasCollectors) {
                startOldCollections = oldCollector.getCollectionCount();
                startOldCollectionsTime = oldCollector.getCollectionTime();
                System.out.println("OpenJDKProbe: Printing startOldCollectionsTime " + startOldCollectionsTime);
            }

            startTime = System.nanoTime();
            if (operatingSystem instanceof com.sun.management.OperatingSystemMXBean) {
                com.sun.management.OperatingSystemMXBean os = (com.sun.management.OperatingSystemMXBean) operatingSystem;
                startProcessCPUTime = os.getProcessCpuTime();
            }
            startJITCTime = jitCompiler.getTotalCompilationTime();

            return true;
        }
    }

    public boolean stopStatistics(boolean warmup) {
        synchronized (this) {
            if (starts.decrementAndGet() > 0)
                return false;

            System.out.println("OpenJDKProbe.stopStatistics() cancelling the scheduler");
            // memoryPoller.cancel(false);
            // scheduler.shutdown();

            System.err.println("- - - - - - - - - - - - - - - - - - - - ");
            System.err.println("Statistics Ended at " + new Date());
            long elapsedTime = System.nanoTime() - startTime;
            System.err.println("Elapsed time: " + TimeUnit.NANOSECONDS.toMillis(elapsedTime) + " ms");
            long elapsedJITCTime = jitCompiler.getTotalCompilationTime() - startJITCTime;
            System.err.println("\tTime in JIT compilation: " + elapsedJITCTime + " ms");
            long elapsedYoungCollectionsTime = -1;
            long youngCollections = -1;
            long elapsedOldCollectionsTime = -1;
            long oldCollections = -1;
            if (hasCollectors) {
                System.out.println("OpenJDKProbe: new youngCollectionTime " + youngCollector.getCollectionTime());
                System.out.println("OpenJDKProbe: new oldCollectionTime " + oldCollector.getCollectionTime());
                elapsedYoungCollectionsTime = youngCollector.getCollectionTime() - startYoungCollectionsTime;
                youngCollections = youngCollector.getCollectionCount() - startYoungCollections;
                System.err.println("\tTime in Young Generation GC: " + elapsedYoungCollectionsTime + " ms (" + youngCollections
                        + " collections)");
                elapsedOldCollectionsTime = oldCollector.getCollectionTime() - startOldCollectionsTime;
                oldCollections = oldCollector.getCollectionCount() - startOldCollections;
                System.err.println("\tTime in Old Generation GC: " + elapsedOldCollectionsTime + " ms (" + oldCollections
                        + " collections)");
            } else {
                System.err.println("\tTime in GC: N/A");
            }

            if (hasMemoryPools) {
                System.err.println("Garbage Generated in Young Generation: " + mebiBytes(totalYoungUsed) + " MiB");
                System.err.println("Garbage Generated in Survivor Generation: " + mebiBytes(totalSurvivorUsed) + " MiB");
                System.err.println("Garbage Generated in Old Generation: " + mebiBytes(totalOldUsed) + " MiB");
            } else {
                System.err.println("Garbage Generated: N/A");
            }

            if (operatingSystem instanceof com.sun.management.OperatingSystemMXBean) {
                com.sun.management.OperatingSystemMXBean os = (com.sun.management.OperatingSystemMXBean) operatingSystem;
                long elapsedProcessCPUTime = os.getProcessCpuTime() - startProcessCPUTime;
                System.err.println("Average CPU Load: " + ((float) elapsedProcessCPUTime * 100 / elapsedTime) + "/"
                        + (100 * operatingSystem.getAvailableProcessors()));
            } else {
                System.err.println("Average CPU Load: N/A");
            }

            System.err.println("----------------------------------------");

            long gcTime = elapsedYoungCollectionsTime + elapsedOldCollectionsTime;
            long mutatorTime = TimeUnit.NANOSECONDS.toMillis(elapsedTime) - gcTime;

//            if (!warmup) {
//                // for plotty
//                System.out.println("============================ MMTk Statistics Totals ============================");
//                long totalGCCollections = youngCollections + oldCollections;
//                System.out.println("GC time.mu time.gc time.jitc time.ygc collections.young time.ogc collections.old youngGenGar.GC survivorGenGar.GC oldGenGar.GC");
//                System.out.println(totalGCCollections + " " + mutatorTime + " " + gcTime + " " + elapsedJITCTime + " " + elapsedYoungCollectionsTime + " " + youngCollections + " " + elapsedOldCollectionsTime + " " + oldCollections + " " + mebiBytes(totalYoungUsed) + " " + mebiBytes(totalYoungUsed) + " " + mebiBytes(totalOldUsed));
//                System.out.println("Total time: " + TimeUnit.NANOSECONDS.toMillis(elapsedTime) + " ms");
//                System.out.println("------------------------------ End MMTk Statistics -----------------------------");
//            }


            // for plotty
            System.out.println("============================ MMTk Statistics Totals ============================");
            long totalGCCollections = youngCollections + oldCollections;
            System.out.println("GC time.mu time.gc time.jitc time.ygc collections.young time.ogc collections.old");
            System.out.println(totalGCCollections + " " + mutatorTime + " " + gcTime + " " + elapsedJITCTime + " " + elapsedYoungCollectionsTime + " " + youngCollections + " " + elapsedOldCollectionsTime + " " + oldCollections);
            System.out.println("Total time: " + TimeUnit.NANOSECONDS.toMillis(elapsedTime) + " ms");
            System.out.println("------------------------------ End MMTk Statistics -----------------------------");

            return true;
        }
    }

    public float percent(long dividend, long divisor) {
        return (float) dividend * 100 / divisor;
    }

    public float mebiBytes(long bytes) {
        return (float) bytes / 1024 / 1024;
    }

    public float gibiBytes(long bytes) {
        return (float) bytes / 1024 / 1024 / 1024;
    }
}
