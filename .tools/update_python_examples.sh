#!/usr/bin/env bash

set -eufx -o pipefail

NEW_VERSION=$1
SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function search_and_replace_version() {
  echo "upgrading Python version of $1 to $NEW_VERSION"
  pushd "$1"

  if [ -e "pyproject.toml" ]; then
    # Use uv for pyproject.toml projects
    uv add "restate-sdk[serde]>=$NEW_VERSION"
  elif [ -e "requirements.txt" ]; then
    sed -i 's/restate[_-]sdk\[serde\][>=!<~][^[:space:]]*/restate-sdk[serde]=='$NEW_VERSION'/' requirements.txt
  fi;

  popd
}

# A2A Python examples
search_and_replace_version $PROJECT_ROOT/a2a

# OpenAI agents Python examples
search_and_replace_version $PROJECT_ROOT/openai-agents/tour-of-agents
search_and_replace_version $PROJECT_ROOT/openai-agents/template

# Pattern Python examples
search_and_replace_version $PROJECT_ROOT/python-patterns
