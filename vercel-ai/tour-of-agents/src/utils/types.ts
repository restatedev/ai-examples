import { z } from "zod";

export const InsuranceClaimSchema = z.object({
  date: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  reason: z.string().nullable().optional(),
  amount: z.number().nullable().optional(),
  placeOfService: z.string().nullable().optional(),
});

export type InsuranceClaim = z.infer<typeof InsuranceClaimSchema>;

const tripExample =
  "Book a business trip to San Francisco from March 15-17. Flying from JFK. And a hotel downtown for 1 guest.";
export const BookingRequest = z.object({
  id: z.string().default("booking_123"),
  prompt: z.string().default(tripExample),
});
export type BookingRequest = z.infer<typeof BookingRequest>;

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
