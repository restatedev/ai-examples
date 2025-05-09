import * as restate from "@restatedev/restate-sdk";
import { serde } from "@restatedev/restate-sdk-zod";
import { z } from "zod";

const ToolResponse = z.object({
  content: z.array(
    z.object({
      type: z.string(),
      text: z.string(),
    })
  ),
});

export type ToolResponse = z.infer<typeof ToolResponse>;

export function tool<I extends z.ZodType>(
  opts: {
    description: string;
    input: I;
  },
  fn: (ctx: restate.Context, input: z.infer<I>) => Promise<ToolResponse>
): typeof fn {
  return restate.handlers.handler(
    {
      description: opts.description,
      input: serde.zod(opts.input),
      output: serde.zod(ToolResponse),
      metadata: {
        "mcp.type": "tool",
      },
    },
    fn
  );
}

