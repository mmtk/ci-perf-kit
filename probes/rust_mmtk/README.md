Rust MMTk Probe
===

The probe expects that the VM binding exposes funcitons with the following signatures: `void harness_begin(long)` and `void harness_end(long)`. The argument is the Java thread ID that calls the harness functions. 

Build
---

Use `make` or `make OPTION=-m32`. 

Run
---

The following parameters are required to run the mmtk probe: 
```
-Djava.library.path=ci-perf-kit/probes/rust_mmtk -Dprobes=RustMMTk -cp ci-perf-kit/probes/probes.jar:ci-perf-kit/probes/rust_mmtk/java:/usr/share/benchmarks/dacapo/dacapo-2006-10-MR2.jar
```

JikesRVM (Probe needs to be built with `-m32`, and Java version needs to be <= 1.6):
```
rvm -Djava.library.path=ci-perf-kit/probes/rust_mmtk -Dprobes=RustMMTk -cp ci-perf-kit/probes/probes.jar:ci-perf-kit/probes/rust_mmtk/java:/usr/share/benchmarks/dacapo/dacapo-2006-10-MR2.jar -Xms500M -Xmx500M Harness -c probe.Dacapo2006Callback fop
```

OpenJDK:

```
java -Djava.library.path=ci-perf-kit/probes/rust_mmtk -Dprobes=RustMMTk -cp ci-perf-kit/probes/probes.jar:ci-perf-kit/probes/rust_mmtk/java:/usr/share/benchmarks/dacapo/dacapo-2006-10-MR2.jar -XX:+UseThirdPartyHeap -server -XX:MetaspaceSize=100M -Xms500M -Xmx500M Harness -c probe.Dacapo2006Callback fop
```