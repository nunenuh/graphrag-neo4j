#!/bin/bash
set -e

# Ensure the data directory exists
mkdir -p data

# New official Papers With Code data source (Hugging Face)
BASE="https://huggingface.co/datasets/paperswithcode/paperswithcode-data/resolve/main"

echo "Downloading official data dumps..."

# Use -Lk to follow redirects and bypass local SSL certificate issues
curl -Lk "$BASE/papers-with-abstracts.json.gz" -o data/papers.json.gz
curl -Lk "$BASE/methods.json.gz"               -o data/methods.json.gz
curl -Lk "$BASE/tasks.json.gz"                 -o data/tasks.json.gz
curl -Lk "$BASE/datasets.json.gz"              -o data/datasets.json.gz
curl -Lk "$BASE/evaluation-tables.json.gz"     -o data/evaluations.json.gz

echo "Extracting files..."
gunzip -f data/*.gz

echo "Done:"
ls -lh data/*.json