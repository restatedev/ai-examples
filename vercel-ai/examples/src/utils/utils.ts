import { z } from "zod";
import { TerminalError } from "@restatedev/restate-sdk";

export const HotelBookingSchema = z.object({
  name: z.string(),
  dates: z.string(),
  guests: z.number(),
});

export type HotelBooking = z.infer<typeof HotelBookingSchema>;

export const FlightBookingSchema = z.object({
  origin: z.string(),
  destination: z.string(),
  date: z.string(),
  passengers: z.number(),
});
export type FlightBooking = z.infer<typeof FlightBookingSchema>;

export async function reserveHotel(
  id: string,
  { name, guests, dates }: HotelBooking,
) {
  console.log(`🏨 Created hotel booking ${id}`);
  return {
    id,
    confirmation: `🏨 Hotel ${name} booked for ${guests} guests on ${dates}`,
  };
}

export async function reserveFlight(
  id: string,
  { origin, destination, date, passengers }: FlightBooking,
) {
  if (destination === "San Francisco" || destination === "SFO") {
    const message = `[👻 SIMULATED] Flight booking failed: No flights to SFO available...`;
    console.error(message);
    throw new TerminalError(message);
  }
  console.log(`✈️ Created flight booking ${id}`);
  return {
    id,
    confirmation: `✈️ Flight from ${origin} to ${destination} on ${date} for ${passengers} passengers`,
  };
}

export async function cancelHotel(id: string) {
  console.log(`🏨 Cancelled hotel booking ${id}`);
}

export async function cancelFlight(id: string) {
  console.log(`✈️ Cancelled flight booking ${id}`);
}
