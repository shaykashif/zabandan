#!/usr/bin/env sh
# Run on the Oracle server to publish the latest site: pulls the repo, which already holds the
# built site in site/. nginx serves it from there, so there's nothing to restart.
set -e
cd "$(dirname "$0")/.."
git pull --ff-only
echo "zabandan.shaykas.com updated to $(git log -1 --format='%h %s')"
