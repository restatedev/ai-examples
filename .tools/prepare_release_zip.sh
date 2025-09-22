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

create_release_zip python/basics python-basics
create_release_zip python/end-to-end-applications/chat-bot python-chat-bot
create_release_zip python/end-to-end-applications/food-ordering python-food-ordering
create_release_zip python/end-to-end-applications/rag-ingestion python-rag-ingestion
create_release_zip python/integrations/deployment-lambda-cdk python-hello-world-lambda-cdk
create_release_zip python/patterns-use-cases python-patterns-use-cases
create_release_zip python/templates/python python-hello-world
create_release_zip python/tutorials/tour-of-restate-python python-tour-of-restate
create_release_zip python/tutorials/tour-of-orchestration-python python-tour-of-orchestration
create_release_zip python/tutorials/tour-of-workflows-python python-tour-of-workflows

create_release_zip typescript/basics typescript-basics
create_release_zip typescript/end-to-end-applications/food-ordering typescript-food-ordering
create_release_zip typescript/end-to-end-applications/chat-bot typescript-chat-bot
create_release_zip typescript/end-to-end-applications/ai-image-workflows typescript-ai-image-workflows
create_release_zip typescript/integrations/deployment-lambda-cdk typescript-hello-world-lambda-cdk
create_release_zip typescript/patterns-use-cases typescript-patterns-use-cases
create_release_zip typescript/templates/node typescript-hello-world
create_release_zip typescript/templates/bun typescript-bun-hello-world
create_release_zip typescript/templates/cloudflare-worker typescript-cloudflare-worker-hello-world
create_release_zip typescript/templates/deno typescript-deno-hello-world
create_release_zip typescript/templates/nextjs typescript-nextjs-hello-world
create_release_zip typescript/tutorials/tour-of-restate-typescript typescript-tour-of-restate
create_release_zip typescript/tutorials/tour-of-orchestration-typescript typescript-tour-of-orchestration
create_release_zip typescript/tutorials/tour-of-workflows-typescript typescript-tour-of-workflows