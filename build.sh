#!/bin/bash
set -e
cd web
npm ci --no-audit --no-fund
npm run build
