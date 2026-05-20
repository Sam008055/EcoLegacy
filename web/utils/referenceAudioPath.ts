import path from 'path'
import { characters, CharacterId } from '@/utils/characters'

/** Absolute path to a character's reference clip under `web/public`. */
export function getReferenceAudioPath(characterId: CharacterId): string {
  const character = characters[characterId] ?? characters.osho
  const relative = character.referenceAudio.startsWith('/')
    ? character.referenceAudio.slice(1)
    : character.referenceAudio
  return path.join(process.cwd(), 'public', relative)
}
