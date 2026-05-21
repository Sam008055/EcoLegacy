'use client'

import { useState, useRef, useEffect } from 'react'
import { createClient } from '@/utils/supabase/client'
import { Mic, Send, LogOut, Loader2, Play, Download } from 'lucide-react'
import { characters, CharacterId } from '@/utils/characters'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { isValidAudioUrl } from '@/utils/errorMessage'
import FeedbackModal from '@/components/FeedbackModal'

type Phase = 'idle' | 'thinking' | 'speaking' | 'animating'

// Quick questions for each character
const getQuickQuestions = (characterId: CharacterId): string[] => {
  const questionMap = {
    osho: ['What is meditation?', 'How to find inner peace?', 'What is love?', 'Who are you?'],
    bhagat_singh: ['What is freedom?', 'Why did you fight?', 'What is patriotism?', 'Who are you?'],
    ssr: ['What is consciousness?', 'Tell me about stars', 'What is quantum physics?', 'Who are you?'],
    tesla: ['What is electricity?', 'How does energy work?', 'What is the future?', 'Who are you?'],
    hitler: ['What was your vision?', 'Why did you start the war?', 'What is leadership?', 'Who are you?']
  };
  return questionMap[characterId] || ['Who are you?', 'What is your philosophy?', 'What is life?'];
};

export default function AvatarInterface({ user, characterId }: { user: any, characterId: CharacterId }) {
  const [query, setQuery] = useState('')
  const [transcript, setTranscript] = useState<{role: 'user' | 'avatar', content: string, audioUrl?: string}[]>([])
  const [phase, setPhase] = useState<Phase>('idle')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [isClient, setIsClient] = useState(false)
  const [isFeedbackOpen, setIsFeedbackOpen] = useState(false)
  
  const character = characters[characterId] || characters.osho; // fallback to osho

  const audioRef = useRef<HTMLAudioElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)

  const router = useRouter()
  const supabase = createClient()

  // Fix hydration mismatch
  useEffect(() => {
    setIsClient(true)
  }, [])

  const handleLogout = async () => {
    await supabase.auth.signOut()
    router.refresh()
    router.push('/')
  }

  const handleFeedbackSubmit = async (rating: number, comment: string) => {
    try {
      await supabase.from('feedback').insert({
        user_id: user.id,
        user_email: user.email,
        character_id: characterId,
        rating,
        comment
      })
    } catch (err) {
      console.error('Failed to submit feedback:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent | string) => {
    let userQuery = '';
    if (typeof e === 'string') {
      userQuery = e;
    } else {
      e.preventDefault();
      userQuery = query;
    }

    if (!userQuery.trim() || phase !== 'idle') return

    setQuery('')
    setTranscript(prev => [...prev, { role: 'user', content: userQuery }])
    setPhase('thinking')
    setAudioUrl(null)
    setVideoUrl(null)

    try {
      // 1. Get Text Response (RAG) - now with caching
      const chatRes = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery, characterId, userEmail: user.email })
      })
      const chatData = await chatRes.json()
      
      if (!chatRes.ok) {
        if (chatRes.status === 429 || chatData.error === 'RATE_LIMIT_REACHED') {
          setTranscript(prev => [...prev, { 
            role: 'avatar', 
            content: "You've reached the maximum limit of 2 free interactions. We'd love to hear your thoughts on the experience so far!"
          }])
          setIsFeedbackOpen(true)
          setPhase('idle')
          return
        }
        if (chatRes.status === 403 || chatData.error === 'CHARACTER_LOCKED') {
          setTranscript(prev => [...prev, { 
            role: 'avatar', 
            content: `You can only interact with one character per account. You're locked to your first choice. Please go back and select that character.`
          }])
          setPhase('idle')
          return
        }
        throw new Error(chatData.error || 'Failed to generate response')
      }
      
      const responseText = chatData.text
      setPhase('speaking')

      // 2. Get Voice (TTS) - now with caching and multiple tokens
      const ttsRes = await fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: responseText, characterId, userEmail: user.email })
      })
      const ttsData = await ttsRes.json()

      if (!ttsRes.ok) {
        // If TTS fails, still show the text response
        console.warn('TTS failed:', ttsData.error)
        setTranscript(prev => [...prev, { 
          role: 'avatar', 
          content: responseText + ' [Audio generation failed - please try again later]'
        }])
        setPhase('idle')
        return
      }
      
      const generatedAudioUrl = ttsData.audioUrl as string | undefined
      if (!isValidAudioUrl(generatedAudioUrl)) {
        console.warn('TTS returned invalid/empty audio')
        setTranscript(prev => [...prev, { 
          role: 'avatar', 
          content: responseText + ' [Audio generation failed - empty response from TTS server]'
        }])
        setPhase('idle')
        return
      }
      setAudioUrl(generatedAudioUrl!)
      
      // Add response to transcript with audio URL for download
      setTranscript(prev => [...prev, { 
        role: 'avatar', 
        content: responseText, 
        audioUrl: generatedAudioUrl 
      }])
      
      setPhase('animating')

      // 3. Get Video (Wav2Lip via Ngrok)
      try {
        const vidRes = await fetch('/api/animate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audioUrl: ttsData.audioUrl, characterId })
        })
        const vidData = await vidRes.json()
        
        if (vidRes.ok && vidData.videoUrl) {
          setVideoUrl(vidData.videoUrl)
        } else if (vidRes.ok && !vidData.videoUrl) {
          // Expected when NGROK/Wav2Lip is not configured — audio still plays
        } else {
          console.warn('Video animation failed, falling back to audio only.')
        }
      } catch (vidErr) {
        console.warn('Video animation failed, falling back to audio only.', vidErr)
      }

      // Automatically display feedback popup after 2nd interaction for non-admins
      if (chatData.interactionsCount === 2 && !chatData.isAdmin) {
        setTimeout(() => setIsFeedbackOpen(true), 2000)
      }

    } catch (err: unknown) {
      console.error(err)
      const msg = err instanceof Error ? err.message : String(err)
      setTranscript(prev => [...prev, { role: 'avatar', content: `[Error: ${msg}]` }])
    } finally {
      setPhase('idle')
    }
  }

  // Auto-play audio when it becomes available (unless video is ready first, though unlikely)
  useEffect(() => {
    if (audioUrl && isValidAudioUrl(audioUrl) && !videoUrl && audioRef.current) {
      audioRef.current.play().catch(e => console.error("Audio autoplay failed", e))
    }
  }, [audioUrl, videoUrl])

  // Auto-play video when it becomes available
  useEffect(() => {
    if (videoUrl && videoRef.current) {
      videoRef.current.play().catch(e => console.error("Video autoplay failed", e))
    }
  }, [videoUrl])

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col h-screen p-4 gap-4">
      {/* Header */}
      <header className="flex justify-between items-center py-4 border-b border-zinc-800">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-zinc-400 hover:text-white text-sm">
            &larr; Back
          </Link>
          <div>
            <h1 className="text-xl font-bold tracking-tighter">Echoes: {character.name}</h1>
            <p className="text-xs text-zinc-500">Authenticated as {user.email}</p>
          </div>
        </div>
        <button onClick={handleLogout} className="text-zinc-400 hover:text-white flex items-center gap-2 text-sm">
          <LogOut size={16} /> Sign out
        </button>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col md:flex-row gap-6 min-h-0">
        
        {/* Avatar Visuals */}
        <div className="w-full md:w-1/2 flex flex-col items-center justify-center bg-zinc-900 rounded-2xl p-4 relative overflow-hidden">
          {videoUrl ? (
            <video 
              ref={videoRef}
              src={videoUrl} 
              className="w-full h-full object-cover rounded-xl"
              controls
              autoPlay
            />
          ) : (
            <div className="relative w-full aspect-square max-w-sm rounded-xl overflow-hidden bg-zinc-800 flex items-center justify-center">
              {/* Placeholder Image */}
              <img 
                src={character.image} 
                alt={character.name} 
                className="absolute inset-0 w-full h-full object-cover opacity-80"
                onError={(e) => {
                  e.currentTarget.src = "https://upload.wikimedia.org/wikipedia/commons/3/33/Osho_in_his_library_1.jpg"
                }}
              />
              
              {/* Status Overlay */}
              {phase !== 'idle' && (
                <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/70 backdrop-blur-md text-white px-4 py-2 rounded-full text-sm flex items-center gap-2 whitespace-nowrap">
                  <Loader2 size={16} className="animate-spin" />
                  {phase === 'thinking' && 'Thinking...'}
                  {phase === 'speaking' && 'Generating Voice...'}
                  {phase === 'animating' && 'Animating Video...'}
                </div>
              )}
            </div>
          )}

          {/* Hidden audio element for fallback when video isn't ready */}
          {audioUrl && !videoUrl && (
            <audio ref={audioRef} src={audioUrl} className="hidden" />
          )}

          {/* Download Audio Button */}
          {audioUrl && (
            <div className="absolute top-4 right-4 z-10">
              <a 
                href={audioUrl} 
                download="response.wav" 
                target="_blank" 
                rel="noreferrer"
                className="p-2 bg-black/60 hover:bg-black/80 backdrop-blur-md rounded-full text-white flex items-center justify-center transition-all shadow-lg"
                title="Download Audio"
              >
                <Download size={18} />
              </a>
            </div>
          )}
        </div>

        {/* Chat Interface */}
        <div className="w-full md:w-1/2 flex flex-col bg-zinc-900 rounded-2xl border border-zinc-800 overflow-hidden">
          {/* Transcript */}
          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            {transcript.length === 0 && (
              <div className="m-auto text-center text-zinc-500 w-full flex flex-col items-center">
                <p className="mb-6">Ask a question to begin the discourse.</p>
                {isClient && (
                  <div className="flex flex-wrap gap-2 justify-center mt-4 max-w-sm">
                    {getQuickQuestions(characterId).map(q => (
                      <button 
                        key={q}
                        onClick={() => handleSubmit(q)}
                        disabled={phase !== 'idle'}
                        className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-sm rounded-full transition-colors border border-zinc-700/50 disabled:opacity-50"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {transcript.map((msg, i) => (
              <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-zinc-500 px-1">
                    {msg.role === 'user' ? 'You' : character.name}
                  </span>
                  {msg.role === 'avatar' && msg.audioUrl && (
                    <a 
                      href={msg.audioUrl} 
                      download={`${character.name}_response_${i}.wav`}
                      className="text-xs text-zinc-400 hover:text-zinc-200 flex items-center gap-1"
                      title="Download audio"
                    >
                      <Download size={12} />
                    </a>
                  )}
                </div>
                <div className={`px-4 py-3 rounded-2xl max-w-[85%] ${
                  msg.role === 'user' 
                    ? 'bg-zinc-100 text-zinc-900 rounded-tr-sm' 
                    : 'bg-zinc-800 text-zinc-100 rounded-tl-sm'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Input Area */}
          <div className="p-4 bg-zinc-950 border-t border-zinc-800">
            <form onSubmit={handleSubmit} className="flex gap-2">
              <button 
                type="button"
                className="p-3 rounded-full bg-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-700 transition-colors"
                title="Voice input coming soon"
              >
                <Mic size={20} />
              </button>
              <input 
                type="text" 
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Message..."
                className="flex-1 bg-zinc-800 border-none rounded-full px-4 text-white focus:outline-none focus:ring-2 focus:ring-zinc-600"
                disabled={phase !== 'idle'}
              />
              <button 
                type="submit"
                disabled={!query.trim() || phase !== 'idle'}
                className="p-3 rounded-full bg-zinc-100 text-zinc-900 hover:bg-white transition-colors disabled:opacity-50"
              >
                <Send size={20} />
              </button>
            </form>
          </div>
        </div>
      </div>

      <FeedbackModal 
        isOpen={isFeedbackOpen} 
        onClose={() => setIsFeedbackOpen(false)} 
        onSubmit={handleFeedbackSubmit} 
      />
    </div>
  )
}
