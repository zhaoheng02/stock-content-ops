#!/bin/bash
set -e
cd web
yarn install --frozen-lockfile --non-interactive
yarn build
