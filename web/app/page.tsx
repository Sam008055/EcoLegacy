import { createClient } from '@/utils/supabase/server'
import { redirect } from 'next/navigation'
import LoginForm from '@/components/LoginForm'
import { characters, CharacterId } from '@/utils/characters'
import Link from 'next/link'

export default async function Home() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-zinc-950 text-white relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-blue-500/10 blur-[100px] rounded-full pointer-events-none"></div>
        <h1 className="text-5xl font-extrabold mb-8 tracking-tighter bg-gradient-to-br from-white to-zinc-500 bg-clip-text text-transparent z-10">EchoLegacy</h1>
        <p className="text-zinc-400 mb-8 max-w-md text-center text-lg leading-relaxed z-10">
          Sign in to interact with digital avatars of historical figures.
        </p>
        <div className="z-10 bg-zinc-900/50 p-8 rounded-2xl border border-zinc-800/50 backdrop-blur-xl shadow-2xl">
          <LoginForm />
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen flex-col items-center py-20 px-4 sm:px-8 bg-zinc-950 text-white relative overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none"></div>
      
      <div className="max-w-6xl w-full z-10">
        <header className="flex justify-between items-center mb-16 border-b border-zinc-800/50 pb-6 backdrop-blur-sm">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tighter bg-gradient-to-br from-white to-zinc-400 bg-clip-text text-transparent">EchoLegacy</h1>
            <p className="text-sm text-zinc-400 mt-2 font-medium tracking-wide">SELECT A PERSONA TO CONVERSE WITH</p>
          </div>
          <form action="/auth/signout" method="post">
            <button type="submit" className="text-zinc-400 hover:text-white text-sm px-4 py-2 rounded-full border border-zinc-800 hover:bg-zinc-800 transition-all duration-300">
              Sign out
            </button>
          </form>
        </header>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {(Object.keys(characters) as CharacterId[]).map((key) => {
            const character = characters[key]
            return (
              <Link key={character.id} href={`/${character.id}`} className="group relative block">
                <div className="absolute inset-0 bg-gradient-to-b from-blue-500/0 to-blue-500/20 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-xl"></div>
                
                <div className="relative bg-zinc-900/80 border border-zinc-800 rounded-2xl overflow-hidden hover:border-zinc-500/50 transition-all duration-500 backdrop-blur-sm group-hover:-translate-y-1 group-hover:shadow-[0_8px_30px_rgb(0,0,0,0.5)] h-full flex flex-col">
                  <div className="aspect-[4/5] relative overflow-hidden bg-zinc-950">
                    <img 
                      src={character.image} 
                      alt={character.name} 
                      className="absolute inset-0 w-full h-full object-cover group-hover:scale-110 transition-transform duration-700 ease-out opacity-90 group-hover:opacity-100"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-zinc-950 via-zinc-950/20 to-transparent opacity-80 group-hover:opacity-60 transition-opacity duration-500"></div>
                    
                    <div className="absolute bottom-0 left-0 right-0 p-6 transform translate-y-2 group-hover:translate-y-0 transition-transform duration-500">
                      <h3 className="text-2xl font-bold tracking-tight text-white mb-2">{character.name}</h3>
                      <p className="text-sm text-zinc-300 line-clamp-3 leading-relaxed opacity-0 group-hover:opacity-100 transition-opacity duration-500 delay-100">
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
