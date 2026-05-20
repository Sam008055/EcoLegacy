import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      // Use production URL if available, otherwise use origin
      const redirectUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.VERCEL_URL 
        ? `https://${process.env.VERCEL_URL || process.env.NEXT_PUBLIC_SITE_URL}${next}`
        : `${origin}${next}`
      
      return NextResponse.redirect(redirectUrl)
    }
  }

  // return the user to an error page with instructions
  const errorUrl = process.env.NEXT_PUBLIC_SITE_URL || process.env.VERCEL_URL
    ? `https://${process.env.VERCEL_URL || process.env.NEXT_PUBLIC_SITE_URL}/auth/auth-code-error`
    : `${origin}/auth/auth-code-error`
    
  return NextResponse.redirect(errorUrl)
}
