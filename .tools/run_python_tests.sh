#!/usr/bin/env bash

set -eufx -o pipefail

SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function python_mypi_lint() {
  if [ -f "pyproject.toml" ]; then
    uv sync
    uv add --dev mypy
    uv run mypy .
  elif [ -f "requirements.txt" ]; then
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    pip install mypy
    python3 -m mypy .
    deactivate
  else
    echo "No pyproject.toml or requirements.txt found in $(pwd)"
    exit 1
  fi
}

# A2A Python examples
#pushd $PROJECT_ROOT/a2a && python_mypi_lint && popd

# OpenAI agents Python examples
pushd $PROJECT_ROOT/openai-agents/template && python_mypi_lint && popd
pushd $PROJECT_ROOT/openai-agents/tour-of-agents && python_mypi_lint && popd
for dir in $PROJECT_ROOT/openai-agents/examples/*/; do
  if [ -f "$dir/pyproject.toml" ]; then
    pushd "$dir" && python_mypi_lint && popd
  fi
done

# Google ADK agents Python examples
pushd $PROJECT_ROOT/google-adk/tour-of-agents && python_mypi_lint && popd

# Pattern Python examples
pushd $PROJECT_ROOT/python-patterns && python_mypi_lint && popd
