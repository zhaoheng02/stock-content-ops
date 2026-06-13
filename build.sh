#!/bin/bash
set -e
cd web
npm install --no-audit --no-fund
npm run build
