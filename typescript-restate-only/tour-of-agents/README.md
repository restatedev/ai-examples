# Durable Restate agents - TypeScript
This repository contains a collection of examples that show how to use Restate to build robust, fault-tolerant AI agents.

These examples use Vercel AI SDK to abstract away the model calls and use the Restate SDK to manage the agent execution and loop.

Check out the [Restate documentation](https://docs.restate.dev/ai) for more information on each example.

## Running the examples

1. Export your OpenAI API key as an environment variable:
   ```shell
   export OPENAI_API_KEY=your_openai_api_key
   ```
2. [Start the Restate Server](https://docs.restate.dev/installation) in a separate shell:
   ```shell
   restate-server
   ```
3. Start the services:
   ```shell
   npm run dev
   ```
4. Register the services (use `--force` if you already had another deployment registered at 9080):
   ```shell
   restate -y deployments register localhost:9080 --force
   ```
5. In the UI, click on the handler to go to the playground, and send a request.
