#!/usr/bin/env bash

set -eufx -o pipefail

NEW_VERSION=$1
SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function search_and_replace_version() {
  echo "upgrading Python version of $1 to $NEW_VERSION"
  if [ -e "$1/requirements.txt" ]; then
    sed -i 's/restate_sdk==[0-9A-Za-z.-]*/restate_sdk=='"$NEW_VERSION"'/' "$1/requirements.txt"
  fi;
  if [ -e "$1/pyproject.toml" ]; then
    sed -i 's/restate-sdk==[0-9A-Za-z.-]*/restate-sdk=='"$NEW_VERSION"'/' "$1/pyproject.toml"
    sed -i 's/restate_sdk\[serde\]>=[0-9A-Za-z.-]*/restate_sdk[serde]>='"$NEW_VERSION"'/' "$1/pyproject.toml"
  fi;
}

# Advanced Python examples
search_and_replace_version $PROJECT_ROOT/advanced/insurance-claims
search_and_replace_version $PROJECT_ROOT/advanced/interruptible-agent
search_and_replace_version $PROJECT_ROOT/advanced/restate-native-agent

# A2A Python examples
search_and_replace_version $PROJECT_ROOT/a2a

# OpenAI agents Python examples
search_and_replace_version $PROJECT_ROOT/openai-agents/examples
search_and_replace_version $PROJECT_ROOT/openai-agents/template

# Pattern Python examples
search_and_replace_version $PROJECT_ROOT/patterns
