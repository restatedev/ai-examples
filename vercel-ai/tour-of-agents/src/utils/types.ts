import { z } from "zod";

export const WeatherPromptSchema = z.object({
  prompt: z.string().default("What is the weather like in San Francisco?"),
});
export type WeatherPrompt = z.infer<typeof WeatherPromptSchema>;

export const ChatMessageSchema = z.object({
  message: z.string().default("Make a poem about durable execution."),
});

export const McpPromptSchema = z.object({
  prompt: z
    .string()
    .default("Show me how to implement a Virtual Object with Restate"),
});
export type McpPrompt = z.infer<typeof McpPromptSchema>;

export const ClaimPromptSchema = z.object({
  prompt: z
    .string()
    .default(
      "Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital.",
    ),
});
export type ClaimPrompt = z.infer<typeof ClaimPromptSchema>;

export const ClaimData = z.object({
  amount: z.number(),
  currency: z.string(),
  reason: z.string(),
  date: z.string(),
})

export const ClaimInputSchema = z.object({
  date: z.string().default("2024-10-01"),
  category: z.string().default("orthopedic"),
  reason: z.string().default("hospital bill for a broken leg"),
  amount: z.number().default(3000),
  placeOfService: z.string().default("General Hospital"),
});
export type ClaimInput = z.infer<typeof ClaimInputSchema>;

export const InsuranceClaimSchema = z.object({
  date: z.string().nullable().optional(),
  category: z.string().nullable().optional(),
  reason: z.string().nullable().optional(),
  amount: z.number().nullable().optional(),
  placeOfService: z.string().nullable().optional(),
});

export type InsuranceClaim = z.infer<typeof InsuranceClaimSchema>;

export const ResearchRequestSchema = z.object({
  topic: z
    .string()
    .default("Benefits of durable execution in distributed systems"),
});

export const CodeGenRequestSchema = z.object({
  task: z
    .string()
    .default(
      "Write a TypeScript function that implements a retry mechanism with exponential backoff",
    ),
});

const tripExample =
  "Book a business trip to San Francisco from March 15-17. Flying from JFK. And a hotel downtown for 1 guest.";
export const BookingRequestSchema = z.object({
  id: z.string().default("booking_123"),
  prompt: z.string().default(tripExample),
});
export type BookingRequest = z.infer<typeof BookingRequestSchema>;

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
