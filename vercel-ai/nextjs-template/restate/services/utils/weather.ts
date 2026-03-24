/**
 * A simple tool that fetches the weather report for a city:
 */
export async function fetchWeather(city: string) {
    return {
      city,
      temperature: 25,
      description: "sunny, warm"
    };
}
