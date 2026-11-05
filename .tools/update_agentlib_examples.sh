#!/usr/bin/env bash

set -eufx -o pipefail

NEW_VERSION=$1
SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

for project in template examples; do
    npm --prefix "$PROJECT_ROOT/agentlib/$project" install "@restatedev/agentlib@^$NEW_VERSION"
done
