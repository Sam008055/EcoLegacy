import { createClient } from '@/utils/supabase/server'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const supabase = await createClient()
  await supabase.auth.signOut()
  
  // Redirect to the home page after signing out
  return NextResponse.redirect(new URL('/', request.url), {
    status: 302,
  })
}
