import { TerminalError } from "@restatedev/restate-sdk";
import * as os from "node:os";
import { parseEnv } from "node:util";

type WeatherResponse = {
  current_condition: {
    temp_C: string;
    weatherDesc: { value: string }[];
  }[];
};

export async function fetchWeather(city: string): Promise<string> {
  // This is a simulated failure to demo Durable Execution retries.
  if (process.env.WEATHER_API_FAIL === "true") {
    console.error(`[👻 SIMULATED] Weather API down...`);
    throw new Error(`[👻 SIMULATED] Weather API down...`);
  }

  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed calling weather API: ${res.status}`);
  const output = await res.text();
  if (output.startsWith("Unknown location")) {
    throw new TerminalError(`Unknown location: ${city}. Please provide a valid city name.`);
  }
  return output;
}

export async function parseWeatherResponse(
  response: string,
): Promise<{ temperature: string; description: string }> {
  const data = JSON.parse(response) as WeatherResponse;
  const current = data.current_condition[0];

  return {
    temperature: current.temp_C,
    description: current.weatherDesc[0].value,
  };
}

function runAgent(prompt: string) {
  let step = callLLM(prompt);

  while (!step.done) {
    callTool(step.tool);
    step = callLLM(prompt, step);
  }
  return step.result;
}

export function callLLM(prompt: string, step?: any): any {
  // Simulate a call to an LLM
  console.log(`Calling LLM with prompt: ${prompt}`);
  return "Hi";
}

function callTool(tool: any): any {
  // Simulate a call to a tool
  console.log(`Calling tool: ${tool.name} with params: ${JSON.stringify(tool.params)}`);
  return { result: "Tool result" };
}
