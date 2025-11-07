import { z } from "zod";
import { serde } from "@restatedev/restate-sdk-zod";

export function utils(examplePrompt: string) {
  return serde.zod(
    z.object({
      message: z.string().default(examplePrompt),
    }),
  );
}

export function printEvaluation(
  iteration: number,
  solution: string,
  evaluation: string,
) {
  console.log(
    `Iteration ${iteration + 1}: Solution: ${solution} Evaluation: ${evaluation}`,
  );
}
