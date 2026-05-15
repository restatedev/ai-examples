#!/usr/bin/env bash

set -eux -o pipefail

SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function npm_install_check() {
    npm install --prefix $1 && npm --prefix $1 run build
}

# Vercel AI TypeScript examples
npm_install_check $PROJECT_ROOT/vercel-ai/template
npm_install_check $PROJECT_ROOT/vercel-ai/nextjs-template
npm_install_check $PROJECT_ROOT/vercel-ai/nextjs-example-app
npm_install_check $PROJECT_ROOT/vercel-ai/tour-of-agents

# Restate-only examples
npm_install_check $PROJECT_ROOT/typescript-restate-only/template
npm_install_check $PROJECT_ROOT/typescript-restate-only/tour-of-agents
for example_dir in $PROJECT_ROOT/typescript-restate-only/examples/*/; do
    npm_install_check "$example_dir"
done
