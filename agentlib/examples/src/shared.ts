import * as restate from "@restatedev/restate-sdk-gen";
import {ToolError, type ApprovalRequest} from "@restatedev/agentlib";
import {openAIModel} from "@restatedev/agentlib/openai";
import {z} from "zod";

// Construction is lazy: importing the examples needs no provider credentials.
export const exampleModel = openAIModel({
  model: process.env.AGENT_MODEL ?? "gpt-5.4",
  retry: {
    maxAttempts: 3,
    initialInterval: {milliseconds: 500},
    exponentiationFactor: 2,
    maxInterval: {seconds: 5},
  },
});

/** Log a ready-to-run approval command from an object handler. */
export function logApprovalCommand(service: string, request: ApprovalRequest): void {
  const key = encodeURIComponent(restate.handlerRequest().key!);
  const decision = JSON.stringify({
    invocationId: request.invocationId,
    signalName: request.signalName,
    approved: true,
  }).replace(/'/g, "'\"'\"'");
  restate.logger().info(
    `Approve ${request.call.name} ${JSON.stringify(request.call.input)} by running:\n` +
      `curl "localhost:8080/${encodeURIComponent(service)}/${key}/approve" --json '${decision}'`,
  );
}

const searchResponse = z.object({
  results: z.array(z.object({title: z.string(), url: z.url(), content: z.string()})),
});

/** Call Tavily from inside an asyncTool so the result is journaled. */
export async function searchTavily(query: string, signal: AbortSignal) {
  // Read credentials inside the side effect; they are never tool arguments.
  const apiKey = process.env.TAVILY_API_KEY;
  if (!apiKey) throw new ToolError("Set TAVILY_API_KEY to use web search.");
  const response = await fetch("https://api.tavily.com/search", {
    method: "POST",
    signal,
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${apiKey}`},
    body: JSON.stringify({query, max_results: 5, include_raw_content: false}),
  });
  // Retry transient failures; report permanent failures to the model.
  if (response.status === 429 || response.status >= 500)
    throw new Error(`Tavily returned HTTP ${response.status}`);
  if (!response.ok) throw new ToolError(`Tavily returned HTTP ${response.status}`);
  const parsed = searchResponse.safeParse(await response.json());
  if (!parsed.success) throw new ToolError("Tavily returned an unexpected response.");
  return parsed.data.results.slice(0, 5).map(({title, url, content}) => ({
    title,
    url,
    content: content.slice(0, 4000),
  }));
}
