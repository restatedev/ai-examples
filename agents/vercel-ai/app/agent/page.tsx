import { redirect } from "next/navigation";

export default function Agent() {
  redirect(`./agent/${crypto.randomUUID()}`);
}
