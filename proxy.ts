import { NextResponse, type NextRequest } from "next/server";
import { VSE_COOKIE, VSE_HOST } from "@/lib/vse";

/**
 * Locale routing. English (default) has clean URLs and is rewritten internally to /en/...;
 * French lives under /fr. An explicit /en prefix redirects to the clean URL so each page has one address.
 */
function route(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const first = pathname.split("/")[1];

  if (first === "fr") return NextResponse.next();

  if (first === "en") {
    const url = request.nextUrl.clone();
    url.pathname = pathname.replace(/^\/en/, "") || "/";
    return NextResponse.redirect(url, 308);
  }

  const url = request.nextUrl.clone();
  url.pathname = `/en${pathname === "/" ? "" : pathname}`;
  return NextResponse.rewrite(url);
}

/**
 * Amplience preview apps open the site with `?vse=<virtual staging domain>` (pinned to the date or edition being
 * previewed). On preview deployments only, remember it in a cookie so the whole session reads that content.
 * `?vse=reset` clears it. The cookie is partitioned and SameSite=None because the site is framed by app.amplience.net.
 */
export function proxy(request: NextRequest) {
  const response = route(request);
  const vse = request.nextUrl.searchParams.get("vse");
  if (vse && process.env.AMPLIENCE_DELIVERY_HOST?.includes("staging")) {
    if (vse === "reset") response.cookies.delete(VSE_COOKIE);
    else if (VSE_HOST.test(vse)) response.cookies.set(VSE_COOKIE, vse, { path: "/", secure: true, sameSite: "none", partitioned: true });
  }
  return response;
}

export const config = {
  // Skip Next internals, the Amplience visualization route and any path with a file extension (images, favicon, etc.)
  matcher: ["/((?!_next|api|preview|.*\\..*).*)"],
};
