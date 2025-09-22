#!/usr/bin/env bash

set -eufx -o pipefail

SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function npm_install_check() {
    npm install --prefix $1 && npm --prefix $1 run build
}

# MCP TypeScript examples
npm_install_check $PROJECT_ROOT/mcp/restate-mcp
npm_install_check $PROJECT_ROOT/mcp/tools

# Vercel AI TypeScript examples
npm_install_check $PROJECT_ROOT/vercel-ai/examples
npm_install_check $PROJECT_ROOT/vercel-ai/template
npm_install_check $PROJECT_ROOT/vercel-ai/template_nextjs
npm_install_check $PROJECT_ROOT/vercel-ai/tour-of-agents
