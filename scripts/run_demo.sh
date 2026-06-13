#!/usr/bin/env bash
set -euo pipefail

python3 -m unittest discover -s tests
python3 -m content_ops run --source data/fixtures/sample_posts.json --out dist --min-score 70
echo "Demo complete. Open dist/daily-manifest.json"
