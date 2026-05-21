import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import LoginForm from '@/components/LoginForm'
import { characters, CharacterId } from '@/utils/characters'
import Link from 'next/link'
import { Sparkles, ArrowRight, BrainCircuit, MessageSquare, Mic } from 'lucide-react'

export default async function Home() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    return (
      <main className="flex min-h-screen flex-col bg-black text-white relative overflow-hidden font-sans selection:bg-indigo-500/30">
        {/* Background effects */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[500px] bg-indigo-500/20 blur-[120px] rounded-full pointer-events-none opacity-50"></div>
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-600/10 blur-[150px] rounded-full pointer-events-none opacity-40"></div>
        
        {/* Navbar */}
        <nav className="relative z-10 flex items-center justify-between px-8 py-6 max-w-7xl mx-auto w-full">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <BrainCircuit className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">EchoLegacy</span>
          </div>
          <div className="hidden sm:flex items-center gap-6 text-sm font-medium text-zinc-400">
            <span className="hover:text-white transition-colors cursor-pointer">About</span>
            <span className="hover:text-white transition-colors cursor-pointer">Technology</span>
            <span className="hover:text-white transition-colors cursor-pointer">Security</span>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 sm:px-8 text-center max-w-5xl mx-auto mt-12 mb-24">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            <span>Next-Generation Voice AI</span>
          </div>
          
          <h1 className="text-5xl sm:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1]">
            Converse with <br className="hidden sm:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-blue-400 to-cyan-400">
              Minds of the Past
            </span>
          </h1>
          
          <p className="text-lg sm:text-xl text-zinc-400 mb-12 max-w-2xl leading-relaxed">
            Experience ultra-realistic, low-latency voice conversations with digital avatars of historical figures, powered by advanced RAG and voice synthesis.
          </p>
          
          <div className="flex flex-col sm:flex-row items-center gap-4 w-full justify-center">
            <div className="w-full sm:w-auto bg-zinc-900/80 p-2 rounded-2xl border border-zinc-800/80 backdrop-blur-xl shadow-2xl flex items-center justify-center">
              <LoginForm />
            </div>
            <button className="w-full sm:w-auto px-8 py-3.5 rounded-full border border-zinc-700 bg-transparent hover:bg-zinc-800/50 text-white font-medium transition-all duration-300 flex items-center justify-center gap-2">
              Learn More <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Features minimal strip */}
        <div className="relative z-10 border-t border-zinc-900 bg-zinc-950/50 backdrop-blur-sm py-12 mt-auto">
          <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4 border border-zinc-800 shadow-inner">
                <Mic className="w-5 h-5 text-indigo-400" />
              </div>
              <h3 className="text-white font-medium mb-2">Ultra-Low Latency</h3>
              <p className="text-sm text-zinc-500">Real-time voice synthesis optimized for natural, flowing conversations.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4 border border-zinc-800 shadow-inner">
                <BrainCircuit className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-white font-medium mb-2">Deep RAG Context</h3>
              <p className="text-sm text-zinc-500">Responses grounded in vast, accurate historical corpuses and original works.</p>
            </div>
            <div className="flex flex-col items-center">
              <div className="w-12 h-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4 border border-zinc-800 shadow-inner">
                <MessageSquare className="w-5 h-5 text-cyan-400" />
              </div>
              <h3 className="text-white font-medium mb-2">Dynamic Avatars</h3>
              <p className="text-sm text-zinc-500">Expressive visual feedback synchronized perfectly with synthesized speech.</p>
            </div>
          </div>
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen flex-col bg-zinc-950 text-white relative overflow-hidden font-sans">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-indigo-500/10 blur-[150px] rounded-full pointer-events-none opacity-60"></div>
      
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-8 py-12 z-10 flex-1 flex flex-col">
        <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-16 gap-6">
          <div className="flex items-center gap-4">
             <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <BrainCircuit className="w-7 h-7 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight text-white">EchoLegacy</h1>
              <p className="text-sm text-zinc-400 mt-1 font-medium flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_10px_rgba(34,197,94,0.6)]"></span>
                System Online. Select Persona.
              </p>
            </div>
          </div>
          <form action="/auth/signout" method="post">
            <button type="submit" className="text-zinc-400 hover:text-white text-sm px-5 py-2.5 rounded-full border border-zinc-800 hover:border-zinc-600 bg-zinc-900/50 hover:bg-zinc-800 transition-all duration-300 font-medium">
              Disconnect
            </button>
          </form>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {(Object.keys(characters) as CharacterId[]).map((key) => {
            const character = characters[key]
            return (
              <Link key={character.id} href={`/${character.id}`} className="group relative block outline-none">
                <div className="absolute -inset-0.5 bg-gradient-to-b from-indigo-500 to-blue-600 rounded-2xl opacity-0 group-hover:opacity-100 group-focus:opacity-100 transition-opacity duration-500 blur-md"></div>
                
                <div className="relative bg-zinc-900 border border-zinc-800 rounded-2xl overflow-hidden transition-all duration-500 h-full flex flex-col shadow-xl group-hover:shadow-2xl">
                  <div className="aspect-[4/5] relative overflow-hidden bg-zinc-950">
                    <img 
                      src={character.image} 
                      alt={character.name} 
                      className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 group-focus:scale-105 transition-transform duration-700 ease-out opacity-80 group-hover:opacity-100 group-focus:opacity-100 mix-blend-luminosity group-hover:mix-blend-normal group-focus:mix-blend-normal"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/40 to-transparent opacity-90 transition-opacity duration-500"></div>
                    
                    <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-md border border-white/10 rounded-full p-2 translate-y-4 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 transition-all duration-300 delay-100">
                      <Mic className="w-4 h-4 text-white" />
                    </div>
                    
                    <div className="absolute bottom-0 left-0 right-0 p-6 flex flex-col justify-end">
                      <h3 className="text-2xl font-bold tracking-tight text-white mb-2 group-hover:text-indigo-300 transition-colors duration-300">{character.name}</h3>
                      <p className="text-sm text-zinc-400 line-clamp-3 leading-relaxed">
                        {character.systemPrompt}
                      </p>
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </main>
  )
}
