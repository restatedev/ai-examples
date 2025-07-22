import * as restate from "@restatedev/restate-sdk";
import { llmCall } from "../util/utils";
import { RestatePromise } from "@restatedev/restate-sdk";

interface ParallelizationRequest {
  prompt: string;
  inputs: string[];
}

/*
Parallelization with Restate

This example demonstrates how to parallelize multiple LLM calls and gather their results.
Restate kicks of all the tasks in parallel and manages their execution to run to completion (retries + recovery).

If you ask it to run the task in 5 different models, and after 3 have given their response, the service crashes.
Then only the 2 remaining tasks will be retried. Restate will have persisted the results of the other 3 tasks.

This example is a translation of the Anthropic AI agents Python notebook examples:
https://github.com/anthropics/anthropic-cookbook/blob/main/patterns/agents/
 */

export const parallelizationService = restate.service({
  name: "ParallelizationService",
  handlers: {
    run_in_parallel: async (
      ctx: restate.Context,
      req: ParallelizationRequest,
    ): Promise<string[]> => {
      const futures = req.inputs.map((item) =>
        ctx.run(`LLM call ${item}`, () =>
          llmCall(`${req.prompt}\nInput: ${item}`),
        ),
      );

      return RestatePromise.all(futures);
    },
  },
});
