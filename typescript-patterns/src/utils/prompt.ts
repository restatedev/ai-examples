import { z } from "zod";
import { serde } from "@restatedev/restate-sdk-zod";

export function prompt(examplePrompt: string) {
  return serde.zod(
    z.object({
      message: z.string().default(examplePrompt),
    }),
  );
}
