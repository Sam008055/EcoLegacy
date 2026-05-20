import { createClient } from '@/utils/supabase/server'
import AvatarInterface from '@/components/AvatarInterface'
import { redirect } from 'next/navigation'
import { CharacterId, characters } from '@/utils/characters'

export default async function CharacterPage({ params }: { params: Promise<{ characterId: string }> }) {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/')
  }

  // Next.js 15 requires awaiting params
  const resolvedParams = await params;
  const characterId = resolvedParams.characterId as CharacterId;
  
  if (!characters[characterId]) {
    redirect('/')
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-between bg-zinc-950 text-white">
      <AvatarInterface user={user} characterId={characterId} />
    </main>
  )
}
