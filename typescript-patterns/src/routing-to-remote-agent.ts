/**
 * Agent Routing
 *
 * Route customer questions to specialized AI agents based on their content.
 * Each routing decision is durable and can be retried if it fails.
 *
 * Flow: Customer Question → Classifier → Specialized Agent → Response
 */
import * as restate from "@restatedev/restate-sdk";
import { ModelMessage } from "ai";
import { Context } from "@restatedev/restate-sdk";
import { createTools, zodPrompt } from "./utils/utils";
import llmCall from "./utils/llm";

const examplePrompt =
  "I can't log into my account. Keep getting invalid password errors.";

// <start_here>
// Define your agents as tools as your AI SDK requires (here Vercel AI SDK)
const SPECIALISTS = {
  BillingAgent: { description: "Expert in payments, charges, and refunds" },
  AccountAgent: { description: "Expert in login issues and security" },
  ProductAgent: { description: "Expert in features and how-to guides" },
} as const;
type Specialist = keyof typeof SPECIALISTS;

async function answer(ctx: Context, { message }: { message: string }) {
  // 1. First, decide if a specialist is needed
  const messages: ModelMessage[] = [
    {
      role: "system",
      content:
        "You are a routing agent. Route the question to a specialist or respond directly if no specialist is needed.",
    },
    { role: "user", content: message },
  ];
  const routingDecision = await ctx.run(
    "Pick specialist",
    // Use your preferred LLM SDK here - specify agents as tools
    async () => llmCall(messages, createTools(SPECIALISTS)),
    { maxRetryAttempts: 3 },
  );

  // 2. No specialist needed? Give a general answer
  if (!routingDecision.toolCalls || routingDecision.toolCalls.length === 0) {
    return routingDecision.text;
  }

  // 3. Get the specialist's name
  const specialist = routingDecision.toolCalls[0].toolName as Specialist;

  // 4. Call the specialist over HTTP
  return ctx.genericCall<string, string>({
    service: specialist,
    method: "run",
    parameter: message,
    inputSerde: restate.serde.json,
    outputSerde: restate.serde.json,
  });
}
// <end_here>

export default restate.service({
  name: "RemoteAgentRouter",
  handlers: {
    answer: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      answer,
    ),
  },
});
