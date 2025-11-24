import { redirect } from "next/navigation";

/**
 * Root page redirects to the strategy builder.
 * 
 * The main entry point for the crypto strategy interpreter is at /strategy,
 * so we redirect users there immediately.
 */
export default function Home() {
  redirect("/strategy");
}

