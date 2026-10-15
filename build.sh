#!/bin/sh
# Builds the site (EN / KZ / RU) into dist/ for a local preview. GitHub Actions runs build.py on every push.
set -e
cd "$(dirname "$0")"
python3 build.py
find dist -name ".DS_Store" -delete
echo "dist/ ready:" && du -sh dist
