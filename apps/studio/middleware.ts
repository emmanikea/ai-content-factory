import { NextRequest, NextResponse } from "next/server";

function unauthorized(message = "Authentication required") {
  return new NextResponse(message, {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="AI Content Factory Studio"' },
  });
}

export function middleware(request: NextRequest) {
  const expectedUser = process.env.STUDIO_BASIC_AUTH_USER;
  const expectedPassword = process.env.STUDIO_BASIC_AUTH_PASSWORD;

  if (!expectedUser || !expectedPassword) {
    if (process.env.NODE_ENV !== "production" && process.env.STUDIO_ALLOW_INSECURE_DEV !== "false") {
      return NextResponse.next();
    }
    return new NextResponse(
      "Studio authentication is not configured. Set STUDIO_BASIC_AUTH_USER and STUDIO_BASIC_AUTH_PASSWORD.",
      { status: 503 },
    );
  }

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Basic ")) return unauthorized();

  try {
    const decoded = atob(authorization.slice(6));
    const separator = decoded.indexOf(":");
    if (separator < 0) return unauthorized();
    const username = decoded.slice(0, separator);
    const password = decoded.slice(separator + 1);
    if (username !== expectedUser || password !== expectedPassword) return unauthorized("Invalid credentials");
  } catch {
    return unauthorized("Invalid credentials");
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
