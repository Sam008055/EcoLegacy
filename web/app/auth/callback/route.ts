import { NextResponse } from 'next/server'
import { createClient } from '@/utils/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/'
  const error = searchParams.get('error')
  const errorDescription = searchParams.get('error_description')

  // Handle auth errors (like flow_state_already_used)
  if (error) {
    console.log(`[AUTH] Auth error: ${error} - ${errorDescription}`)
    
    // If flow state already used, redirect to home (user is likely already logged in)
    if (error === 'invalid_request' && errorDescription?.includes('flow_state_already_used')) {
      const redirectUrl = `https://eco-legacy-alpha.vercel.app${next}`
      
      console.log(`[AUTH] Flow state already used, redirecting to: ${redirectUrl}`)
      return NextResponse.redirect(redirectUrl)
    }
    
    // For other errors, redirect to error page
    const errorUrl = `https://eco-legacy-alpha.vercel.app/auth/auth-code-error`
      
    return NextResponse.redirect(errorUrl)
  }

  if (code) {
    const supabase = await createClient()
    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)
    
    if (!exchangeError) {
      // Use production URL if available, otherwise use origin
      const redirectUrl = process.env.NEXT_PUBLIC_SITE_URL 
        ? `${process.env.NEXT_PUBLIC_SITE_URL.replace(/\/$/, '')}${next}`
        : `${origin}${next}`
      
      console.log(`[AUTH] Auth successful, redirecting to: ${redirectUrl}`)
      return NextResponse.redirect(redirectUrl)
    } else {
      console.error(`[AUTH] Code exchange failed:`, exchangeError)
    }
  }

  // return the user to an error page with instructions
  const errorUrl = `https://eco-legacy-alpha.vercel.app/auth/auth-code-error`
    
  return NextResponse.redirect(errorUrl)
}
