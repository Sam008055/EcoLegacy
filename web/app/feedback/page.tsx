import { createClient } from '@/utils/supabase/server'
import { cookies } from 'next/headers'
import Link from 'next/link'
import { Star, ArrowLeft } from 'lucide-react'

export default async function FeedbackPage() {
  const supabase = await createClient()

  // Verify admin access
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user || user.email !== 'samarthpasalkar4@gmail.com') {
    return (
      <div className="min-h-screen bg-zinc-950 p-6 md:p-12 flex items-center justify-center">
        <div className="text-center bg-zinc-900 border border-red-900/50 p-8 rounded-3xl max-w-md w-full">
          <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-zinc-400 mb-6">This page is restricted to administrators only.</p>
          <Link href="/" className="px-4 py-2 bg-indigo-500 hover:bg-indigo-600 text-white rounded-full font-medium transition-colors">
            Return Home
          </Link>
        </div>
      </div>
    )
  }

  const { data: feedbackData, error } = await supabase
    .from('feedback')
    .select('*')
    .order('created_at', { ascending: false })

  return (
    <div className="min-h-screen bg-zinc-950 p-6 md:p-12">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-4 mb-10">
          <Link href="/" className="p-2 text-zinc-500 hover:text-white bg-zinc-900 rounded-full transition-colors border border-zinc-800">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-3xl font-bold text-white tracking-tight">Feedback Hub</h1>
            <p className="text-zinc-400 mt-1">Recent feedback from user conversations.</p>
          </div>
        </div>

        {/* Feedback Grid */}
        {error ? (
          <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400">
            Failed to load feedback: {error.message}
          </div>
        ) : !feedbackData || feedbackData.length === 0 ? (
          <div className="p-12 bg-zinc-900 border border-zinc-800 rounded-3xl text-center flex flex-col items-center">
            <div className="w-16 h-16 bg-zinc-800 rounded-full flex items-center justify-center mb-4">
              <Star size={24} className="text-zinc-600" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">No feedback yet</h3>
            <p className="text-zinc-400">Once users complete a conversation and submit feedback, it will appear here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {feedbackData.map((item) => (
              <div 
                key={item.id} 
                className="bg-zinc-900/50 border border-zinc-800/80 rounded-3xl p-6 relative overflow-hidden group hover:bg-zinc-900 hover:border-zinc-700 transition-all"
              >
                {/* Subtle gradient effect on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
                
                <div className="flex justify-between items-start mb-4 relative z-10">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star 
                        key={star} 
                        size={18} 
                        className={star <= item.rating ? 'fill-indigo-400 text-indigo-400' : 'text-zinc-800'} 
                      />
                    ))}
                  </div>
                  <span className="text-xs font-medium px-2.5 py-1 bg-zinc-800 text-zinc-400 rounded-full">
                    {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>
                
                <p className="text-zinc-300 relative z-10 leading-relaxed">
                  {item.comment ? `"${item.comment}"` : <span className="text-zinc-600 italic">No comment provided</span>}
                </p>
                
                <div className="mt-6 pt-4 border-t border-zinc-800/50 flex justify-between items-center relative z-10">
                  <span className="text-xs text-zinc-500 font-mono">
                    Character: <span className="text-zinc-300">{item.character_id}</span>
                  </span>
                  {item.user_email && (
                    <span className="text-xs text-zinc-500 truncate max-w-[50%]">
                      By: <span className="text-zinc-300">{item.user_email}</span>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
