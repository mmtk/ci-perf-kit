package probe;

public class RustMMTkProbe implements Probe {
    static {
        System.loadLibrary("rust_mmtk_probe");
    }

    public void begin(String benchmark, int iteration, boolean warmup) {
        if (warmup)
            return;

        begin_native(benchmark, iteration, warmup, Thread.currentThread().getId());
    }

    public void end(String benchmark, int iteration, boolean warmup) {
        if (warmup)
            return;

        end_native(benchmark, iteration, warmup, Thread.currentThread().getId());
    }

    public void report(String benchmark, int iteration, boolean warmup) {}
    public void init() {}
    public void cleanup() {}

    public native void begin_native(String benchmark, int iteration, boolean warmup, long threadId);
    public native void end_native(String benchmark, int iteration, boolean warmup, long threadId);
}