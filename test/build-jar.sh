#!/usr/bin/env bash
# Compile the module's Java (the CALT analyzer) into lib/UPD78XX.jar so that a Ghidra install with
# this directory linked/copied under Ghidra/Processors/ picks it up for the test harness. The
# release route is `gradle buildExtension` (tools/build-module.sh).
#   GHIDRA_INSTALL_DIR=... [JAVA_HOME=a JDK with javac] test/build-jar.sh
set -euo pipefail
: "${GHIDRA_INSTALL_DIR:?set GHIDRA_INSTALL_DIR}"
MOD=$(cd "$(dirname "$0")/.." && pwd)
G=$GHIDRA_INSTALL_DIR/Ghidra
CP=$(find "$G/Framework" "$G/Features/Base" -name '*.jar' ! -name '*-src*' | tr '\n' ':')
JAVAC=javac; JAR=jar
if [[ -n ${JAVAC_HOME:-} ]]; then JAVAC=$JAVAC_HOME/bin/javac; JAR=$JAVAC_HOME/bin/jar; fi
OUT=$(mktemp -d "${TMPDIR:-/tmp}/UPD78XX-jar.XXXXXX")
trap 'rm -rf "$OUT"' EXIT
"$JAVAC" -nowarn --release 21 -cp "$CP" -d "$OUT" $(find "$MOD/src/main/java" -name '*.java')
mkdir -p "$MOD/lib"
"$JAR" cf "$MOD/lib/UPD78XX.jar.tmp" -C "$OUT" .
mv "$MOD/lib/UPD78XX.jar.tmp" "$MOD/lib/UPD78XX.jar"
echo "built $MOD/lib/UPD78XX.jar"
