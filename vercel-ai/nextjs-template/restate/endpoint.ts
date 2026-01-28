import * as restate from "@restatedev/restate-sdk/fetch";
import { agent } from "@/restate/services/agent";

export const endpoint = restate.createEndpointHandler({ services: [agent] });