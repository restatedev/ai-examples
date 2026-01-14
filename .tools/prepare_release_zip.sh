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

# OpenAI agents examples
create_release_zip openai-agents/tour-of-agents python-openai-agents-tour-of-agents
create_release_zip openai-agents/template python-openai-agents-template

# Google ADK examples
create_release_zip google-adk/tour-of-agents python-google-adk-tour-of-agents

# Pattern examples
create_release_zip python-patterns python-patterns

# Vercel AI examples
create_release_zip vercel-ai/examples typescript-vercel-ai-examples
create_release_zip vercel-ai/template typescript-vercel-ai-template
create_release_zip vercel-ai/template_nextjs typescript-vercel-ai-template-nextjs
create_release_zip vercel-ai/tour-of-agents typescript-vercel-ai-tour-of-agents