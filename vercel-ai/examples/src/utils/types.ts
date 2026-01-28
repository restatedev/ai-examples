import { z } from "zod";

const example =
  "Book a business trip to San Francisco from March 15-17. Flying from JFK. And a hotel downtown for 1 guest.";
export const BookingRequest = z.object({
  id: z.string().default("booking_123"),
  prompt: z.string().default(example),
});
export type BookingRequest = z.infer<typeof BookingRequest>;
