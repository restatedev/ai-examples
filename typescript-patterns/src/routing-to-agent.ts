/**
 * Agent Routing
 *
 * Route customer questions to specialized AI agents based on their content.
 * Each routing decision is durable and can be retried if it fails.
 *
 * Flow: Customer Question → Classifier → Specialized Agent → Response
 */
import * as restate from "@restatedev/restate-sdk";
import { Context } from "@restatedev/restate-sdk";
import { createTools, zodPrompt } from "./utils/utils";
import llmCall from "./utils/llm";

const examplePrompt =
  "I can't log into my account. Keep getting invalid password errors.";

// <start_here>
const SPECIALISTS = {
  billingAgent: {
    description: "Expert in payments, charges, and refunds",
    prompt:
      "You are a billing support agent specializing in payments, charges, and refunds.",
  },
  accountAgent: {
    description: "Expert in login issues and security",
    prompt:
      "You are an account support agent specializing in login issues and security.",
  },
  productAgent: {
    description: "Expert in features and how-to guides",
    prompt:
      "You are a product support agent specializing in features and how-to guides.",
  },
} as const;

type Specialist = keyof typeof SPECIALISTS;

async function answer(ctx: Context, { message }: { message: string }) {
  // 1. First, decide if a specialist is needed
  const routingDecision = await ctx.run(
    "Pick specialist",
    // Use your preferred LLM SDK here - specify agents as tools
    async () => llmCall(message, createTools(SPECIALISTS)),
    { maxRetryAttempts: 3 },
  );

  // 2. No specialist needed? Give a general answer
  if (!routingDecision.toolCalls || routingDecision.toolCalls.length === 0) {
    return routingDecision.text;
  }

  // 3. Get the specialist's name
  const specialist = routingDecision.toolCalls[0].toolName as Specialist;

  // 4. Ask the specialist to answer
  const { text } = await ctx.run(
    `Ask ${specialist}`,
    async () =>
      llmCall([
        { role: "user", content: message },
        { role: "system", content: SPECIALISTS[specialist].prompt },
      ]),
    { maxRetryAttempts: 3 },
  );

  return text;
}
// <end_here>

export default restate.service({
  name: "AgentRouter",
  handlers: {
    answer: restate.createServiceHandler(
      { input: zodPrompt(examplePrompt) },
      answer,
    ),
  },
});
