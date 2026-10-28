#!/usr/bin/env bash
# Rebuild the public database from the release package and deploy it to Fly.io.
# Usage: bash deploy/deploy.sh <release version, e.g. v0.1.0-draft>
# First time only: flyctl apps create cccc-program-corpus
#                  flyctl secrets set -a cccc-program-corpus DATASETTE_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))")
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${1:?release version}"
APP_DIR=build/flyapp
rm -rf "$APP_DIR" && mkdir -p "$APP_DIR"
python -I src/deploy_db.py "build/release/cccc-program-corpus-$VERSION" build/stats.json "$APP_DIR/cccc.db"
python -I -c "import json,sys,yaml; json.dump(yaml.safe_load(open('deploy/metadata.yml',encoding='utf-8')),open(sys.argv[1],'w',encoding='utf-8'),ensure_ascii=False,indent=2)" "$APP_DIR/metadata.json"
cp deploy/Dockerfile deploy/fly.toml "$APP_DIR/"
(cd "$APP_DIR" && flyctl deploy --remote-only --ha=false)
