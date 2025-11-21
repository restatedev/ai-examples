/**
 * Competitively racing agents
 *
 * Run two approaches in parallel and return the fastest response.
 * Cancel the slower tasks to save resources.
 */
import * as restate from "@restatedev/restate-sdk";
import { Context, RestatePromise } from "@restatedev/restate-sdk";
import llmCall from "./utils/llm";
import { zodPrompt } from "./utils/utils";

const examplePrompt = "What's the best approach to learn machine learning?";

// <start_here>
async function run(
  ctx: Context,
  { message }: { message: string },
): Promise<string> {
  // Start both service calls concurrently
  const slowCall = ctx.serviceClient(racingAgent).thinkLonger({ message });
  const slowResponse = slowCall.map((res) => ({ tag: "slow", res }));

  const fastCall = ctx.serviceClient(racingAgent).respondQuickly({ message });
  const fastResponse = fastCall.map((res) => ({ tag: "fast", res }));

  const pending = [slowResponse, fastResponse];

  // Wait for the first one to complete
  const { tag, res } = await RestatePromise.any(pending);

  if (tag === "fast") {
    console.log("Quick response won the race!");
    const slowInvocationId = await slowCall.invocationId;
    ctx.cancel(slowInvocationId);
  } else {
    console.log("Deep analysis won the race!");
    const quickInvocationId = await fastCall.invocationId;
    ctx.cancel(quickInvocationId);
  }

  return res ?? "LLM gave no response";
}
// <end_here>

async function thinkLonger(
  ctx: Context,
  { message }: { message: string },
): Promise<string> {
  const { text } = await ctx.run(
    "Deep analysis",
    async () => llmCall(`Analyze this thoroughly: ${message}`),
    { maxRetryAttempts: 3 },
  );
  return text;
}

async function respondQuickly(
  ctx: Context,
  { message }: { message: string },
): Promise<string> {
  const { text } = await ctx.run(
    "Quick response",
    async () => llmCall(`Quick answer: ${message}`),
    { maxRetryAttempts: 3 },
  );
  return text;
}

const racingAgent = restate.service({
  name: "RacingAgent",
  handlers: {
    run: restate.createServiceHandler({ input: zodPrompt(examplePrompt) }, run),
    thinkLonger,
    respondQuickly,
  },
});

export default racingAgent;
