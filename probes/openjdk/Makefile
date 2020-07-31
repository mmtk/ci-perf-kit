all: OpenJDKProbe.class

JAVAC=$(JAVA_HOME)/bin/javac

OpenJDKProbe.class:
	$(JAVAC) -cp ../probes.jar java/probe/OpenJDKProbe.java

clean:
	rm java/probe/OpenJDKProbe.class