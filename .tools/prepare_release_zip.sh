#!/usr/bin/env bash

OUT_DIR="$(pwd)"

gitzip() {
  # Uses git to zip current working directory.
  # This automatically excludes files excluded by .gitignore
  git archive HEAD -o $1.zip
}

# create_release_zip $input_dir $template-name
# Stores result in $OUT_DIR
create_release_zip() {
  pushd $1 && gitzip $2 && popd || exit
  mv "$1/$2.zip" "$OUT_DIR/$2.zip"
  echo "Zip for $1 in $OUT_DIR/$2.zip"
}

# Advanced examples
create_release_zip advanced/insurance-claims python-advanced-insurance-claims
create_release_zip advanced/interruptible-agent python-advanced-interruptible-agent
create_release_zip advanced/restate-native-agent python-advanced-restate-native-agent

# A2A examples
create_release_zip a2a/a2a python-a2a

# MCP examples
create_release_zip mcp/restate-mcp typescript-restate-mcp

# OpenAI agents examples
create_release_zip openai-agents/examples python-openai-agents-examples
create_release_zip openai-agents/template python-openai-agents-template

# Pattern examples
create_release_zip patterns python-patterns

# Vercel AI examples
create_release_zip vercel-ai/examples typescript-vercel-ai-examples
create_release_zip vercel-ai/template typescript-vercel-ai-template
create_release_zip vercel-ai/template_nextjs typescript-vercel-ai-template-nextjs
create_release_zip vercel-ai/tour-of-agents typescript-vercel-ai-tour-of-agents