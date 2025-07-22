import * as restate from "@restatedev/restate-sdk";
import { llmCall, extractXml } from "../util/utils";

interface RouteRequest {
  input: string;
  routes: Record<string, string>;
}

export const routingService = restate.service({
  name: "RoutingService",
  handlers: {
    route: async (ctx: restate.Context, req: RouteRequest): Promise<string> => {
      // Route input to specialized prompt using content classification
      console.log(`\nAvailable routes: ${Object.keys(req.routes)}`);

      const selectorPrompt = `
                Analyze the input and select the most appropriate support team from these options: ${Object.keys(req.routes)}
                First explain your reasoning, then provide your selection in this XML format:
        
                <reasoning>
                Brief explanation of why this ticket should be routed to a specific team.
                Consider key terms, user intent, and urgency level.
                </reasoning>
        
                <selection>
                The chosen team name
                </selection>.
        
                Input: ${req.input}`.trim();

      const routeResponse = await ctx.run("Determine routing", () =>
        llmCall(selectorPrompt),
      );

      const reasoning = extractXml(routeResponse, "reasoning");
      const routeKey = extractXml(routeResponse, "selection")
        .trim()
        .toLowerCase();

      console.log("Routing Analysis:");
      console.log(reasoning);
      console.log(`\nSelected route: ${routeKey}`);

      // Option 1: Process input with selected specialized prompt
      const selectedPrompt = req.routes[routeKey];
      return ctx.run("Route", () =>
        llmCall(`${selectedPrompt}\nInput: ${req.input}`),
      );

      // Option 2: In Restate, this could also be a call to run a tool (service handler)
      // Have a look at the more advanced examples in this repo to see how far you can go with this
      // const [serviceName, taskName] = req.routes[routeKey].split("/");
      // const taskResponse = await ctx.serviceClient(serviceName)[taskName](req.input);
    },
  },
});

export default routingService;
