import { withMiddlewareAuthRequired } from "@auth0/nextjs-auth0/edge";
import { NextResponse } from "next/server";

/*
 * DEV-ONLY preview bypass.
 *
 * When active, auth is NOT required so the dashboard can be rendered and
 * visually verified locally without a configured Auth0 tenant.
 *
 * SAFETY: the bypass requires BOTH conditions below to be true:
 *   1. process.env.NODE_ENV !== "production"  -- Next.js forces NODE_ENV to
 *      "production" for every production build (`next build` / `next start`),
 *      so this is false in any deployed/production build.
 *   2. process.env.NEXT_PUBLIC_DEV_PREVIEW === "1"  -- an explicit opt-in that
 *      must be set deliberately in a local .env.local.
 * Because condition 1 can never hold in a production build, it is impossible
 * to activate this bypass in production even if the flag were somehow set.
 */
const DEV_PREVIEW =
  process.env.NODE_ENV !== "production" &&
  process.env.NEXT_PUBLIC_DEV_PREVIEW === "1";

export default DEV_PREVIEW
  ? // Dev preview: let every matched request through without auth.
    () => NextResponse.next()
  : withMiddlewareAuthRequired();

export const config = {
  // Protect everything except login, API auth routes, and the /demo route (Firebase Auth)
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|demo).*)",
  ],
};
