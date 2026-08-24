import { auth } from "@/auth";
import { NextResponse } from "next/server";

/**
 * Gate the chat page behind authentication and bounce logged-in users away
 * from the login page. (Next 16 renamed the middleware file convention to
 * proxy; this is the same edge-of-request gate under the new name.)
 */
export default auth((request) => {
  const { nextUrl } = request;
  const isLoggedIn = Boolean(request.auth);

  if (nextUrl.pathname.startsWith("/chat") && !isLoggedIn) {
    return NextResponse.redirect(new URL("/login", nextUrl));
  }

  if (nextUrl.pathname === "/login" && isLoggedIn) {
    return NextResponse.redirect(new URL("/chat", nextUrl));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/chat/:path*", "/login"],
};
