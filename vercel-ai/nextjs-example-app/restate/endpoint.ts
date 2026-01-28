import * as restate from "@restatedev/restate-sdk/fetch";
import agent from "@/restate/services/agent";
import { createPubsubObject } from "@restatedev/pubsub";

const pubsub = createPubsubObject("pubsub", {});

export const endpoint = restate.createEndpointHandler({
  services: [agent, pubsub],
});
