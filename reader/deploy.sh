#!/usr/bin/env bash
# Build reader.db from a release package and deploy the reader to Fly.io.
# Usage: bash reader/deploy.sh <release version, e.g. v0.1.0-draft>
# First time only: flyctl apps create cccc-program-reader
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${1:?release version}"
OUT=build/readerapp
rm -rf "$OUT" && mkdir -p "$OUT/data"
python -I reader/build_reader.py "build/release/cccc-program-corpus-$VERSION" "$OUT/data/reader.db" ../CCCC-Program-Capture data/suppressed_people.csv
cp -r reader/app.py reader/analytics.py reader/templates reader/static reader/requirements.txt reader/Dockerfile reader/fly.toml "$OUT/"
(cd "$OUT" && flyctl deploy --remote-only --ha=false)
