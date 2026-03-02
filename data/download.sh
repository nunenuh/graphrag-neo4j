#!/bin/bash
set -e

# Ensure the data directory exists
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$SCRIPT_DIR"

# Source: pwc-archive on Hugging Face (last public snapshot, Jul 2025)
BASE="https://huggingface.co/datasets/pwc-archive/files/resolve/main"

echo "Downloading Papers With Code data dumps..."

curl -Lk "$BASE/jul-29-papers-with-abstracts.json.gz" -o "$SCRIPT_DIR/papers.json.gz"
curl -Lk "$BASE/jul-28-methods.json.gz"               -o "$SCRIPT_DIR/methods.json.gz"
curl -Lk "$BASE/jul-28-datasets.json.gz"              -o "$SCRIPT_DIR/datasets.json.gz"
curl -Lk "$BASE/jul-28-evaluation-tables.json.gz"     -o "$SCRIPT_DIR/evaluations.json.gz"

echo "Extracting gz files..."
gunzip -f "$SCRIPT_DIR"/*.gz

echo "Generating tasks.json from evaluation tables..."
python3 -c "
import json, sys
with open('$SCRIPT_DIR/evaluations.json') as f:
    data = json.load(f)
seen, tasks = set(), []
for item in data:
    name = item.get('task', '')
    if name and name not in seen:
        seen.add(name)
        tasks.append({
            'id': name,
            'name': name,
            'area': ', '.join(item.get('categories', [])),
            'description': (item.get('description') or '')[:1000],
        })
with open('$SCRIPT_DIR/tasks.json', 'w') as f:
    json.dump(tasks, f, indent=2)
print(f'Generated {len(tasks)} tasks')
"

echo ""
echo "Done:"
ls -lh "$SCRIPT_DIR"/*.json
