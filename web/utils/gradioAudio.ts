/** Extract output audio path/URL from Gradio F5-TTS predict() result. */
export function extractGradioAudioPath(result: unknown): string | null {
  if (result == null) return null

  const pick = (item: unknown): string | null => {
    if (typeof item === 'string') return item
    if (item && typeof item === 'object') {
      const o = item as Record<string, unknown>
      if (typeof o.path === 'string') return o.path
      if (typeof o.url === 'string') return o.url
      if (typeof o.name === 'string') return o.name
    }
    return null
  }

  if (Array.isArray(result)) {
    return pick(result[0])
  }

  if (typeof result === 'object' && result !== null) {
    const r = result as Record<string, unknown>
    if (Array.isArray(r.data)) {
      return pick(r.data[0])
    }
  }

  return null
}
