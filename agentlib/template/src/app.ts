import { serve } from "@restatedev/restate-sdk";
import { weatherService } from "./agent.js";

await serve({ services: [weatherService], port: 9080 });
