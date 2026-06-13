#!/usr/bin/env bash
set -euo pipefail

BATCH_NAME="${1:-$(date +%Y-%m-%d)}"
ACCOUNTS_FILE="${ACCOUNTS_FILE:-config/x_accounts.example.csv}"
INBOX_FILE="${INBOX_FILE:-data/inbox/${BATCH_NAME}-x-posts.json}"
OUT_DIR="${OUT_DIR:-dist/${BATCH_NAME}}"
MIN_SCORE="${MIN_SCORE:-70}"
LIMIT="${LIMIT:-20}"

if [[ -f ".env" ]]; then
  set -a
  source .env
  set +a
fi

python3 -m content_ops collect-x \
  --accounts "${ACCOUNTS_FILE}" \
  --out "${INBOX_FILE}" \
  --max-results-per-account "${MAX_RESULTS_PER_ACCOUNT:-5}"

python3 -m content_ops run \
  --source "${INBOX_FILE}" \
  --out "${OUT_DIR}" \
  --min-score "${MIN_SCORE}" \
  --limit "${LIMIT}" \
  --batch-name "${BATCH_NAME}" \
  --use-gpt

echo "Daily batch complete: ${OUT_DIR}/${BATCH_NAME}-manifest.json"
