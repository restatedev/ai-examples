#!/usr/bin/env bash

set -eufx -o pipefail

NEW_VERSION=$1
SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function search_and_replace_version() {
  echo "upgrading Python version of $1 to $NEW_VERSION"
  pushd "$1"
  # Use uv for pyproject.toml projects
  uv add "restate-sdk[serde]>=$NEW_VERSION"
  popd
}

# A2A Python examples
search_and_replace_version $PROJECT_ROOT/a2a

# OpenAI agents Python examples
search_and_replace_version $PROJECT_ROOT/openai-agents/tour-of-agents
while IFS= read -r dir; do
  search_and_replace_version "$dir"
done < <(find "$PROJECT_ROOT/openai-agents/examples" -mindepth 2 -maxdepth 2 -name pyproject.toml -exec dirname {} \;)
search_and_replace_version $PROJECT_ROOT/openai-agents/template

# Google ADK agents Python examples
search_and_replace_version $PROJECT_ROOT/google-adk/tour-of-agents

# Pattern Python examples
search_and_replace_version $PROJECT_ROOT/python-patterns
