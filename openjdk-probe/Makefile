all: java/probe/OpenJDKProbe.class

JAVAC=$(JAVA_HOME)/bin/javac
# anupli/probes submodule, for the probe.Probe interface
PROBES_JAR=../probes/out/probes.jar

java/probe/OpenJDKProbe.class: java/probe/OpenJDKProbe.java
	$(JAVAC) -cp $(PROBES_JAR) $<

clean:
	rm -f java/probe/OpenJDKProbe.class
