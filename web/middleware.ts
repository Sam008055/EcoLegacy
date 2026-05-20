import { NextResponse, type NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  // Simple pass-through middleware
  // Auth token refresh is handled by the server-side Supabase client in each page
  return NextResponse.next()
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|mp3|mpeg|wav)$).*)',
  ],
}
