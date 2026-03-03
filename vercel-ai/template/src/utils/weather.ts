/**
 * A simple tool that fetches the weather report for a city:
 */

// <start_weather>
export async function fetchWeather(city: string) {
  failOnDenver(city);
  return `The weather in ${city} is sunny and warm.`
}
// <end_weather>

function failOnDenver(city: string) {
  if (city === "Denver") {
    const message = `[👻 SIMULATED] "Fetching weather failed: Weather API down..."`;
    console.error(message);
    throw new Error(message);
  }
}