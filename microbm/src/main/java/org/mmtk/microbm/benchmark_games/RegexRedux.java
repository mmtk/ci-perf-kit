/*
   The Computer Language Benchmarks Game
   https://salsa.debian.org/benchmarksgame-team/benchmarksgame/

   contributed by Francois Green
*/
package org.mmtk.microbm.benchmark_games;
import java.io.*;
import java.util.*;
import java.util.concurrent.CompletableFuture;
import java.util.Map.Entry;
import java.util.function.*;
import java.util.regex.*;

import static java.util.stream.Collectors.*;

import org.openjdk.jmh.infra.Blackhole;
import org.openjdk.jmh.annotations.*;

@BenchmarkMode(Mode.AverageTime)
public class RegexRedux {

  @Benchmark
  public static void run(Blackhole blackhole) throws IOException {
    ByteArrayOutputStream baos = new ByteArrayOutputStream();
    {
        File initialFile = new File("data/knucleotide-input.txt");
        InputStream targetStream = new FileInputStream(initialFile);
        
        byte[] buf = new byte[65536];
        int count;
        while ((count = targetStream.read(buf)) > 0) {
            baos.write(buf, 0, count);
        }
    }
    final String input = baos.toString("US-ASCII");

    final int initialLength = input.length();

    final String sequence = input.replaceAll(">.*\n|\n", "");

    CompletableFuture<String> replacements = CompletableFuture.supplyAsync(() -> {
        final Map<String, String> iub = new LinkedHashMap<>();
        iub.put("tHa[Nt]", "<4>");
        iub.put("aND|caN|Ha[DS]|WaS", "<3>");
        iub.put("a[NSt]|BY", "<2>");
        iub.put("<[^>]*>", "|");
        iub.put("\\|[^|][^|]*\\|", "-");

        String buffer = sequence;
        for (Map.Entry<String, String> entry : iub.entrySet()) {
            buffer = Pattern.compile(entry.getKey()).matcher(buffer).replaceAll(entry.getValue());
        }
        return buffer;
    });

    final int codeLength = sequence.length();

    final List<String> variants = Arrays.asList("agggtaaa|tttaccct",
                                                "[cgt]gggtaaa|tttaccc[acg]",
                                                "a[act]ggtaaa|tttacc[agt]t",
                                                "ag[act]gtaaa|tttac[agt]ct",
                                                "agg[act]taaa|ttta[agt]cct",
                                                "aggg[acg]aaa|ttt[cgt]ccct",
                                                "agggt[cgt]aa|tt[acg]accct",
                                                "agggta[cgt]a|t[acg]taccct",
                                                "agggtaa[cgt]|[acg]ttaccct");

    BiFunction<String, String, Entry<String, Long>> counts = (v, s) -> {
      Long count = Pattern.compile(v).splitAsStream(s).count() - 1; //Off by one
      return new AbstractMap.SimpleEntry<>(v, count);
    };

    final Map<String, Long> results = variants.parallelStream()
                                              .map(variant -> counts.apply(variant, sequence))
                                              .collect(toMap(Map.Entry::getKey, Map.Entry::getValue));

    variants.forEach(variant -> blackhole.consume(variant + " " + results.get(variant)));

    blackhole.consume(initialLength);
    blackhole.consume(codeLength);
    blackhole.consume(replacements.join().length());
  }
}