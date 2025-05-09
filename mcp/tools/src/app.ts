import * as restate from "@restatedev/restate-sdk";
import { z } from "zod";
import { tool } from "./api";

const greet = tool(
  {
    description: "Greets a person by name",
    input: z.object({ name: z.string() }),
  },
  async (ctx, { name }) => {
    const seen = await ctx.objectClient(personObject, name).increment();

    return {
      content: [
        {
          type: "text",
          text: `Hello, ${name} at the ${seen}th time !`,
        },
      ],
    };
  }
);


const personObject = restate.object({
  name: "person",
  handlers: {
    /**
     * This isn't a tool, but restate's virtual object!
     * 
     * With it you can store data and create handlers that can be called from other tools.
     * 
     * These objects are keyed and keep state isolated per-key.
     * 
     * You can use them for:
     * 
     * - Storing session data
     * - Remembering important context *per user* (key)
     * - Coordinating complex workflows
     * - And more! 
     *  
     * @param ctx this object's context
     * @returns the number of times the person has been seen
     */
    increment: async (ctx: restate.ObjectContext) => {
      const seen = (await ctx.get<number>("seenCount")) ?? 0;
      ctx.set("seenCount", seen + 1);
      return seen;
    },
  },
});


// Create a service that binds the tool to the virtual object

const tools = restate.service({
  name: "tools",
  handlers: {
    greet,
  },
});

restate.endpoint()
.bind(tools)
.bind(personObject)
.listen();
