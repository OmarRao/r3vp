import { withMiddlewareAuthRequired } from "@auth0/nextjs-auth0/edge";

export default withMiddlewareAuthRequired();

export const config = {
  // Protect everything except login, API auth routes, and the /demo route (Firebase Auth)
  matcher: [
    "/((?!api/auth|_next/static|_next/image|favicon.ico|demo).*)",
  ],
};
