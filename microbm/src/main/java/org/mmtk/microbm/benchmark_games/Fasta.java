/*
 * The Computer Language Benchmarks Game
 * https://salsa.debian.org/benchmarksgame-team/benchmarksgame/
 * 
 * modified by Mehmet D. AKIN
 * modified by Daryl Griffith
 */
package org.mmtk.microbm.benchmark_games;
 
import java.io.IOException;
import java.io.OutputStream;
import java.io.ByteArrayOutputStream;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.atomic.AtomicInteger;
import org.openjdk.jmh.infra.Blackhole;

import org.openjdk.jmh.annotations.*;

@State(Scope.Benchmark)
@BenchmarkMode(Mode.AverageTime)
public class Fasta {
    @State(Scope.Benchmark)
    public static class BenchmarkState {
        static final int LINE_LENGTH = 60;
        static final int LINE_COUNT = 1024;
        static final int BUFFERS_IN_PLAY = 6;
        static final int IM = 139968;
        static final int IA = 3877;
        static final int IC = 29573;
        static final float ONE_OVER_IM = 1f / IM;
        
        final AtomicInteger IN = new AtomicInteger();
        final AtomicInteger OUT = new AtomicInteger();
        int last = 42;
        final NucleotideSelector[] WORKERS = new NucleotideSelector[
            Runtime.getRuntime().availableProcessors() > 1 
            ? Runtime.getRuntime().availableProcessors() - 1 
            : 1];
        
        @Setup(Level.Trial)
        public void setUp() {
            for (int i = 0; i < WORKERS.length; i++) {
                WORKERS[i] = new NucleotideSelector();
                WORKERS[i].setDaemon(true);
                WORKERS[i].start();
            }
        }
    }

    @Param({"25000000"})
    private int size;

    @Benchmark
    public void run(Blackhole blackhole, BenchmarkState st) {
        int n = size;

        try (OutputStream writer = new ByteArrayOutputStream()) {
            final int bufferSize = BenchmarkState.LINE_COUNT * BenchmarkState.LINE_LENGTH;

            for (int i = 0; i < BenchmarkState.BUFFERS_IN_PLAY; i++) {
                lineFillALU(st, new AluBuffer(BenchmarkState.LINE_LENGTH, bufferSize, i * bufferSize));
            }
            speciesFillALU(st, writer, n * 2, ">ONE Homo sapiens alu\n");
            for (int i = 0; i < BenchmarkState.BUFFERS_IN_PLAY; i++) {
                writeBuffer(st, writer);
                lineFillRandom(st, new Buffer(true, BenchmarkState.LINE_LENGTH, bufferSize));
            }
            speciesFillRandom(st, writer
                    , n * 3
                    , ">TWO IUB ambiguity codes\n"
                    , true);
            for (int i = 0; i < BenchmarkState.BUFFERS_IN_PLAY; i++) {
                writeBuffer(st, writer);
                lineFillRandom(st, new Buffer(false, BenchmarkState.LINE_LENGTH, bufferSize));
            }
            speciesFillRandom(st, writer
                    , n * 5
                    , ">THREE Homo sapiens frequency\n"
                    , false);
            for (int i = 0; i < BenchmarkState.BUFFERS_IN_PLAY; i++) {
                writeBuffer(st, writer);
            }
            blackhole.consume(writer);
        } catch (IOException ex) {
        }
     }

    private static void lineFillALU(BenchmarkState st, AbstractBuffer buffer) {
        st.WORKERS[st.OUT.incrementAndGet() % st.WORKERS.length].put(buffer);
    }

    private static void bufferFillALU(BenchmarkState st, OutputStream writer, int buffers) throws IOException {
        AbstractBuffer buffer;

        for (int i = 0; i < buffers; i++) {
            buffer = st.WORKERS[st.IN.incrementAndGet() % st.WORKERS.length].take();
            writer.write(buffer.nucleotides);
            lineFillALU(st, buffer);
        }
    }

    private static void speciesFillALU(BenchmarkState st, final OutputStream writer
            , final int nChars
            , final String name) throws IOException {
        final int bufferSize = BenchmarkState.LINE_COUNT * BenchmarkState.LINE_LENGTH;
        final int bufferCount = nChars / bufferSize;
        final int bufferLoops = bufferCount - BenchmarkState.BUFFERS_IN_PLAY;
        final int charsLeftover = nChars - (bufferCount * bufferSize);

        writer.write(name.getBytes());
        bufferFillALU(st, writer, bufferLoops);
        if (charsLeftover > 0) {
            writeBuffer(st, writer);
            lineFillALU(st,
                    new AluBuffer(BenchmarkState.LINE_LENGTH
                            , charsLeftover
                            , nChars - charsLeftover));
        }
    }

    private static void lineFillRandom(BenchmarkState st, Buffer buffer) {
        for (int i = 0; i < buffer.randoms.length; i++) {
            st.last = (st.last * BenchmarkState.IA + BenchmarkState.IC) % BenchmarkState.IM;
            buffer.randoms[i] = st.last * BenchmarkState.ONE_OVER_IM;
        }
        st.WORKERS[st.OUT.incrementAndGet() % st.WORKERS.length].put(buffer);
    }

    private static void bufferFillRandom(BenchmarkState st, OutputStream writer
            , int loops) throws IOException {
        AbstractBuffer buffer;

        for (int i = 0; i < loops; i++) {
            buffer = st.WORKERS[st.IN.incrementAndGet() % st.WORKERS.length].take();
            writer.write(buffer.nucleotides);
            lineFillRandom(st, (Buffer) buffer);
        }
    }

    private static void speciesFillRandom(BenchmarkState st, final OutputStream writer
            , final int nChars
            , final String name
            , final boolean isIUB) throws IOException {
        final int bufferSize = BenchmarkState.LINE_COUNT * BenchmarkState.LINE_LENGTH;
        final int bufferCount = nChars / bufferSize;
        final int bufferLoops = bufferCount - BenchmarkState.BUFFERS_IN_PLAY;
        final int charsLeftover = nChars - (bufferCount * bufferSize);

        writer.write(name.getBytes());
        bufferFillRandom(st, writer, bufferLoops);
        if (charsLeftover > 0) {
            writeBuffer(st, writer);    
            lineFillRandom(st, new Buffer(isIUB, BenchmarkState.LINE_LENGTH, charsLeftover));
        }
    }

    private static void writeBuffer(BenchmarkState st, OutputStream writer) throws IOException {
        writer.write(
                st.WORKERS[st.IN.incrementAndGet() % st.WORKERS.length]
                        .take()
                        .nucleotides);
    }

    public static class NucleotideSelector extends Thread {

        private final BlockingQueue<AbstractBuffer> 
                in = new ArrayBlockingQueue<>(BenchmarkState.BUFFERS_IN_PLAY);
        private final BlockingQueue<AbstractBuffer> 
                out = new ArrayBlockingQueue<>(BenchmarkState.BUFFERS_IN_PLAY);

        public void put(AbstractBuffer line) {
            try {
                in.put(line);
            } catch (InterruptedException ex) {
            }
        }

        @Override
        public void run() {
            AbstractBuffer line;

            try {
                for (;;) {
                    line = in.take();
                    line.selectNucleotides();
                    out.put(line);
                }
            } catch (InterruptedException ex) {
            }
        }

        public AbstractBuffer take() {
            try {
                return out.take();
            } catch (InterruptedException ex) {
            }
            return null;
        }
    }

    public abstract static class AbstractBuffer {

        final int LINE_LENGTH;
        final int LINE_COUNT;
        byte[] chars;
        final byte[] nucleotides;
        final int CHARS_LEFTOVER;

        public AbstractBuffer(final int lineLength, final int nChars) {
            LINE_LENGTH = lineLength;
            final int outputLineLength = lineLength + 1;
            LINE_COUNT = nChars / lineLength;
            CHARS_LEFTOVER = nChars % lineLength;
            final int nucleotidesSize 
                    = nChars + LINE_COUNT + (CHARS_LEFTOVER == 0 ? 0 : 1);
            final int lastNucleotide = nucleotidesSize - 1;

            nucleotides = new byte[nucleotidesSize];
            for (int i = lineLength
                    ; i < lastNucleotide
                    ; i += outputLineLength) {
                nucleotides[i] = '\n';
            }
            nucleotides[nucleotides.length - 1] = '\n';
        }

        public abstract void selectNucleotides();
    }

    public static class AluBuffer extends AbstractBuffer {

        final String ALU =
                "GGCCGGGCGCGGTGGCTCACGCCTGTAATCCCAGCACTTTGG"
                + "GAGGCCGAGGCGGGCGGATCACCTGAGGTCAGGAGTTCGAGA"
                + "CCAGCCTGGCCAACATGGTGAAACCCCGTCTCTACTAAAAAT"
                + "ACAAAAATTAGCCGGGCGTGGTGGCGCGCGCCTGTAATCCCA"
                + "GCTACTCGGGAGGCTGAGGCAGGAGAATCGCTTGAACCCGGG"
                + "AGGCGGAGGTTGCAGTGAGCCGAGATCGCGCCACTGCACTCC"
                + "AGCCTGGGCGACAGAGCGAGACTCCGTCTCAAAAA";
        final int MAX_ALU_INDEX = ALU.length() - LINE_LENGTH;
        final int ALU_ADJUST = LINE_LENGTH - ALU.length();
        final int nChars;
        int charIndex;
        int nucleotideIndex;

        public AluBuffer(final int lineLength
                , final int nChars
                , final int offset) {
            super(lineLength, nChars);
            this.nChars = nChars;
            chars = (ALU + ALU.substring(0, LINE_LENGTH)).getBytes();
            charIndex = offset % ALU.length();
        }

        @Override
        public void selectNucleotides() {
            nucleotideIndex = 0;
            for (int i = 0; i < LINE_COUNT; i++) {
                ALUFillLine(LINE_LENGTH);
            }
            if (CHARS_LEFTOVER > 0) {
                ALUFillLine(CHARS_LEFTOVER);
            }
            charIndex = (charIndex + (nChars * (BenchmarkState.BUFFERS_IN_PLAY - 1))) 
                    % ALU.length();
        }

        private void ALUFillLine(final int charCount) {
            System.arraycopy(chars
                    , charIndex
                    , nucleotides
                    , nucleotideIndex
                    , charCount);
            charIndex += charIndex < MAX_ALU_INDEX ? charCount : ALU_ADJUST;
            nucleotideIndex += charCount + 1;
        }
    }

    public static class Buffer extends AbstractBuffer {

        final byte[] iubChars = new byte[]{
            'a', 'c', 'g', 't',
            'B', 'D', 'H', 'K',
            'M', 'N', 'R', 'S',
            'V', 'W', 'Y'};
        final double[] iubProbs = new double[]{
            0.27, 0.12, 0.12, 0.27,
            0.02, 0.02, 0.02, 0.02,
            0.02, 0.02, 0.02, 0.02,
            0.02, 0.02, 0.02,};
        final byte[] sapienChars = new byte[]{
            'a',
            'c',
            'g',
            't'};
        final double[] sapienProbs = new double[]{
            0.3029549426680,
            0.1979883004921,
            0.1975473066391,
            0.3015094502008};
        final float[] probs;
        final float[] randoms;
        final int charsInFullLines;

        public Buffer(final boolean isIUB
                , final int lineLength
                , final int nChars) {
            super(lineLength, nChars);
            double cp = 0;
            final double[] dblProbs = isIUB ? iubProbs : sapienProbs;

            chars = isIUB ? iubChars : sapienChars;
            probs = new float[dblProbs.length];
            for (int i = 0; i < probs.length; i++) {
                cp += dblProbs[i];
                probs[i] = (float) cp;
            }
            probs[probs.length - 1] = 2f;
            randoms = new float[nChars];
            charsInFullLines = (nChars / lineLength) * lineLength;
        }

        @Override
        public void selectNucleotides() {
            int i, j, m;
            float r;
            int k;

            for (i = 0, j = 0; i < charsInFullLines; j++) {
                for (k = 0; k < LINE_LENGTH; k++) {
                    r = randoms[i++];
                    for (m = 0; probs[m] < r; m++) {
                    }
                    nucleotides[j++] = chars[m];
                }
            }
            for (k = 0; k < CHARS_LEFTOVER; k++) {
                r = randoms[i++];
                for (m = 0; probs[m] < r; m++) {
                }
                nucleotides[j++] = chars[m];
            }
        }
    }
}