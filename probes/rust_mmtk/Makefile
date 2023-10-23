all: native/librust_mmtk_probe.so RustMMTkProbe.class

CFLAGS=-O2 -g -fPIC
JAVAC=$(JAVA_HOME)/bin/javac

ifeq (-m32,$(findstring -m32,$(OPTION)))
CFLAGS += -m32
endif

native/librust_mmtk_probe.so: native/rust_mmtk_probe.c
	gcc $(CFLAGS) -pthread -c native/rust_mmtk_probe.c -I$(JAVA_HOME)/include -I$(JAVA_HOME)/include/linux/
	gcc $(CFLAGS) -pthread -shared -o librust_mmtk_probe.so rust_mmtk_probe.o -lc

RustMMTkProbe.class:
	$(JAVAC) -cp ../probes.jar java/probe/RustMMTkProbe.java

clean:
	rm librust_mmtk_probe.so
	rm rust_mmtk_probe.o
	rm java/probe/RustMMTkProbe.class