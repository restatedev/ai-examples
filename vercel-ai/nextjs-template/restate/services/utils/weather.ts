import { TerminalError } from "@restatedev/restate-sdk";

/**
 * A simple tool that fetches the weather report for a city:
 */
export async function fetchWeather(city: string) {
  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
  const res = await fetch(url);

  if (!res.ok){
    throw new Error(`Failed calling weather API: ${res.status}`);
  }
  const output = await res.text();
  if (output.startsWith("Unknown location")) {
    throw new TerminalError(
      `Unknown location: ${city}. Please provide a valid city name.`,
    );
  }

  try {
    const data = JSON.parse(output);
    const current = data["current_condition"][0];

    return {
      temperature: current["temp_C"],
      description: current["weatherDesc"][0]["value"]
    };
  } catch (e) {
    throw new TerminalError("Could not parse weather API response", { cause: e })
  }
}
