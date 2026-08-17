/**
 * Edge guard for the console.
 *
 * Everything under the `(dashboard)` route group is behind a session. The
 * matcher below is a *negative* list — public routes and build assets are
 * named, everything else is protected — so a page added tomorrow is guarded
 * the moment it exists. That mirrors the backend, where routes are protected
 * by middleware and opened by an explicit allowlist.
 *
 * This is UX, not security: it decides what HTML a browser is sent, and the
 * session cookie it reads is not signature-verified (the edge runtime holds no
 * secret). Data is protected by the backend's authentication middleware, which
 * verifies every request regardless of what the browser was allowed to render.
 */

import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { SESSION_COOKIE, isTokenExpired } from "@/lib/session";

/** Routes that must stay reachable without a session. */
const PUBLIC_ROUTES = ["/login", "/register"];

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(`${route}/`))) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE)?.value;
  if (!isTokenExpired(token)) {
    return NextResponse.next();
  }

  // Send them to /login and remember where they were headed, so the round trip
  // through the login form lands them back on the page they asked for.
  const loginUrl = request.nextUrl.clone();
  loginUrl.pathname = "/login";
  loginUrl.search = "";
  if (pathname !== "/") {
    loginUrl.searchParams.set("next", `${pathname}${search}`);
  }

  const response = NextResponse.redirect(loginUrl);
  // An expired cookie is worse than none: it keeps failing this check on every
  // navigation. Clear it on the way out.
  if (token) response.cookies.delete(SESSION_COOKIE);
  return response;
}

export const config = {
  matcher: [
    /*
     * Match every path except:
     *   - /login, /register          (the way in)
     *   - /_next/*                   (build output, HMR)
     *   - /api/*                     (proxied to the backend, which guards itself)
     *   - files with an extension    (favicon.ico, images, fonts, robots.txt)
     */
    "/((?!login|register|_next/static|_next/image|api/|.*\\.[\\w]+$).*)",
  ],
};
