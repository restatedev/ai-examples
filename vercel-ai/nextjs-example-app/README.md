# Restate and Vercel AI SDK examples

A set of examples illustrating how to use [Restate](https://restate.dev/) to add durable execution, state, and communication to agents built with the [Vercel AI SDK](https://ai-sdk.dev)

## Setting up an Environment

### Starting Restate Server

```shell
npx @restatedev/restate-server@latest
```

### Starting the Agents NextJS app

The project is a basic Next.js project, bootstrapped form the standard template.

```bash
npm install
npm run dev
```

The entry point is in the [restate/v1](app/restate/v1/[[...services]]/route.ts) route.

### Register the AI SDK agents at Restate

```shell
npx @restatedev/restate deployments register http://localhost:3000/restate/v1 --use-http1.1
```

Or use the UI on `localhost:9070` to register the services.

## Agent Example

Code: [agent.ts](restate/services/agent.ts)

This example demonstrates an AI agent with tool use and real-time streaming updates via pubsub.

### Key Features

1. **Durable Service Handler**: The AI agent function runs as a Restate durable service handler, providing durable retries and enabling all further features.

   ```typescript
   export default restate.service({
     name: "agent",
     handlers: {
       chat: restate.handlers.handler(
         {
           /* schema */
         },
         async (ctx: restate.Context, { prompt, topic }) => {
           return await runAgent(ctx, prompt, topic);
         },
       ),
     },
   });
   ```

2. **Durable LLM Calls**: We wrap the LLM model to make sure all inference steps are durably journaled:

   ```typescript
   const model = wrapLanguageModel({
     model: openai("gpt-4o-2024-08-06"),
     middleware: durableCalls(ctx, { maxRetryAttempts: 3 }),
   });
   ```

3. **Durable Tool Execution**: Tool calls are wrapped into durable steps (`ctx.run(...)`)

   ```typescript
   execute: async ({ expression }) => {
     return await ctx.run(
       `evaluating ${expression}`,
       async () => mathjs.evaluate(expression),
       { serde: superJson }
     );
   },
   ```

4. **Real-time Updates via PubSub**: The agent publishes intermediate results to a pubsub topic:
   ```typescript
   onStepFinish: async (step) => {
     step.toolCalls.forEach((toolCall) => {
       pubsub.publish(topic, {
         role: "assistant",
         content: `Tool call: ${toolCall.toolName}(${JSON.stringify(toolCall.input)})`
       }, ctx.rand.uuidv4());
     });
   },
   ```

### Using the Web UI

Navigate to `http://localhost:3000/agent/<topic>` where `<topic>` is any unique identifier for your conversation (e.g., `http://localhost:3000/agent/my-session`).

The UI provides:

- A chat interface to interact with the agent
- Real-time streaming of the agent's reasoning and tool calls
- Persistent message history via the pubsub stream

### Invoking via HTTP

You can also invoke the agent directly via HTTP:

```shell
curl localhost:8080/agent/chat --json '{ "prompt": "A taxi driver earns $9461 per 1-hour of work. If he works 12 hours a day and in 1 hour he uses 12 liters of petrol with a price of $134 for 1 liter. How much money does he earn in one day?", "topic": "my-session" }'
```

Or use the UI playground in the Restate UI on `localhost:9070`

### Investigating the execution

Use the _Invocations_ tab in the UI to see ongoing invocations. Adjust the filter below to also show finished (succeeded) invocations.

## PubSub Stream

The pubsub stream is implemented using Restate's pubsub library (see [endpoint.ts](./restate/endpoint.ts)).

The stream is accessible via the [/pubsub/[topic]](app/pubsub/[topic]/route.ts) route, which provides Server-Sent Events (SSE) for real-time updates.

The web UI at `/agent/[topic]` subscribes to this stream to display messages in real-time.
