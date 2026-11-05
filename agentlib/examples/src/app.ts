import {serve} from "@restatedev/restate-sdk";
import {services} from "./lessons/services.js";

await serve({services, port: 9080});
