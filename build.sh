#!/usr/bin/env bash
# Rebuild build/corpus.db from the private capture folder. Run from the project root.
set -euo pipefail
CAPTURE="${CAPTURE:-../CCCC-Program-Capture}"
rm -f build/corpus.db
python -I src/parse_eshow.py "$CAPTURE" build/corpus.db
python -I src/load_conventions.py build/corpus.db data/conventions.csv
if [ "${SKIP_DETAILS:-0}" != 1 ]; then python -I src/parse_details.py "$CAPTURE" build/corpus.db; fi
python -I src/extract_pdfs.py "$CAPTURE" build/pdf
python -I src/parse_pdf.py build/pdf build/corpus.db
python -I src/merge_pdf_titles.py build/corpus.db 2024 2025 2026
python -I src/match_ror.py build/corpus.db data/ror_cache.jsonl
python -I src/apply_aliases.py build/corpus.db data/affiliation_aliases.csv data/ror_query_cache.jsonl
python -I src/enrich_ipeds.py build/corpus.db data/ipeds/HD2023.zip data/wikidata_ror_ipeds.csv
python -I src/build_persons.py build/corpus.db
python -I src/stats.py build/corpus.db build/stats.json
python -I src/export.py build/corpus.db build/export
