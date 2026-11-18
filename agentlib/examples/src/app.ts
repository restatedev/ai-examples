import {createServer} from "node:http";
import {serve} from "@restatedev/restate-sdk";
import {agUiHandler} from "./lessons/18_ag_ui.js";
import {services} from "./lessons/services.js";

await serve({services, port: 9080});
// Example 18's AG-UI endpoint, a client of the Restate ingress.
createServer(agUiHandler(process.env.RESTATE_CALL_URL ?? "http://localhost:8080")).listen(9081);
