import * as restate from "@restatedev/restate-sdk";
import { llmCall } from "../util/utils";

export const callChainingService = restate.service({
  name: "CallChainingService",
  handlers: {
    chain_call: async (
      ctx: restate.Context,
      req: { input: string; prompts: string[] },
    ) => {
      let result = req.input;
      for (let i = 0; i < req.prompts.length; i++) {
        const prompt = req.prompts[i];
        result = await ctx.run(`LLM call ${i + 1}`, () =>
          llmCall(`${prompt}\nInput: ${result}`),
        );
        console.log(result);
      }
      return result;
    },
  },
});
