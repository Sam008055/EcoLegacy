'use client'

import { createClient } from '@/utils/supabase/client'
import { useState } from 'react'

export default function LoginForm() {
  const [loading, setLoading] = useState(false)
  const supabase = createClient()

  const handleLogin = async () => {
    setLoading(true)
    await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
  }

  return (
    <button
      onClick={handleLogin}
      disabled={loading}
      className="bg-white text-zinc-900 px-6 py-3 rounded-full font-medium hover:bg-zinc-200 transition-colors disabled:opacity-50 flex items-center gap-2"
    >
      {loading ? 'Connecting...' : 'Sign in with Google'}
    </button>
  )
}
