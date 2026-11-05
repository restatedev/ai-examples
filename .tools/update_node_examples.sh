#!/usr/bin/env bash

set -eufx -o pipefail

NEW_VERSION=$1
SELF_PATH=${BASH_SOURCE[0]:-"$(command -v -- "$0")"}
PROJECT_ROOT="$(dirname "$SELF_PATH")/.."

function bump_restate_sdk_deps() {
    local project_dir=$1
    local package_json="$project_dir/package.json"

    # Check if package.json exists
    if [ ! -f "$package_json" ]; then
        echo "No package.json found in $project_dir"
        return
    fi

    # Keep runtime and test SDK packages on the same version.
    local dependency_type deps dep save_flag
    for dependency_type in dependencies devDependencies; do
        deps=$(node -e '
            const fs = require("fs");
            const pkg = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
            console.log(Object.keys(pkg[process.argv[2]] || {})
                .filter(dep => dep.startsWith("@restatedev/restate-sdk"))
                .join(" "));
        ' "$package_json" "$dependency_type")
        save_flag=--save-prod
        if [ "$dependency_type" = devDependencies ]; then
            save_flag=--save-dev
        fi
        for dep in $deps; do
            echo "Installing $dep@^$NEW_VERSION in $project_dir"
            npm --prefix "$project_dir" install "$save_flag" "$dep@^$NEW_VERSION"
        done
    done
}

# agentlib examples
bump_restate_sdk_deps "$PROJECT_ROOT/agentlib/template"
bump_restate_sdk_deps "$PROJECT_ROOT/agentlib/examples"

# Vercel AI TypeScript examples
bump_restate_sdk_deps $PROJECT_ROOT/vercel-ai/template
bump_restate_sdk_deps $PROJECT_ROOT/vercel-ai/nextjs-template
bump_restate_sdk_deps $PROJECT_ROOT/vercel-ai/nextjs-example-app
bump_restate_sdk_deps $PROJECT_ROOT/vercel-ai/tour-of-agents

# Restate-only examples
bump_restate_sdk_deps $PROJECT_ROOT/typescript-restate-only/template
bump_restate_sdk_deps $PROJECT_ROOT/typescript-restate-only/tour-of-agents
for example_dir in $PROJECT_ROOT/typescript-restate-only/examples/*/; do
    bump_restate_sdk_deps "$example_dir"
done
