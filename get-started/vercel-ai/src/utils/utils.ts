type WeatherResponse = {
  current_condition: {
    temp_C: string;
    weatherDesc: { value: string }[];
  }[];
};

export async function fetchWeather(city: string): Promise<string> {
  const url = `https://wttr.in/${encodeURIComponent(city)}?format=j1`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed calling weather API: ${res.status}`);
  return res.text();
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
