Micro Benchmarks
-----

These Java micro benchmarks are implemented with the JMH framework. We include benchamrks from these sources:
* Computer Language Benchmark Games (https://benchmarksgame-team.pages.debian.net/benchmarksgame/fastest/java.html)
  * We only include benchmarks that do a fair amount of allocations (as our focus is GC).
* Richards benchmarks
* GCBench (both single threaded and multi threaded versions)