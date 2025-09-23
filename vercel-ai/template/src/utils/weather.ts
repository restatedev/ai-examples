import { TerminalError } from "@restatedev/restate-sdk";

/**
 * A simple tool that fetches the weather report for a city:
 */

// <start_weather>
export async function fetchWeather(city: string) {
  failOnDenver(city);
  const output = await fetchWeatherFromAPI(city);
  return parseWeatherResponse(output);
}
// <end_weather>

function failOnDenver(city: string) {
  if (city === "Denver") {
    const message = `[👻 SIMULATED] "Fetching weather failed: Weather API down..."`;
    console.error(message);
    throw new Error(message);
  }
}

async function fetchWeatherFromAPI(city: string) {
  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
  const res = await fetch(url);
  const output = await res.text();
  if (!res.ok) {
    if (res.status === 404 && output) {
      throw new TerminalError(
          `Unknown location: ${city}. Please provide a valid city name.`,
      );
    }
    throw new Error(`Weather API returned status ${res.status}`);
  }
  return output;
}

async function parseWeatherResponse(output: string) {
  try {
    const data = JSON.parse(output);
    const current = data.current_condition?.[0];

    if (!current) {
      throw new Error("Missing current weather data");
    }

    return {
      temperature: current.temp_C,
      description: current.weatherDesc?.[0]?.value,
    };
  } catch (e) {
    throw new TerminalError("Could not parse weather API response", {
      cause: e,
    });
  }
}