/** Safely read an error message without mutating DOMException-like objects. */
export function getErrorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  if (typeof err === 'object' && err !== null && 'message' in err) {
    const msg = (err as { message: unknown }).message
    if (typeof msg === 'string') return msg
  }
  return String(err)
}

/** True if a data-URL or remote audio URL has enough payload to play. */
export function isValidAudioUrl(url: string | null | undefined): boolean {
  if (!url || typeof url !== 'string') return false
  if (url.startsWith('data:audio')) {
    const base64 = url.split(',')[1] ?? ''
    return base64.length > 100
  }
  return url.startsWith('http')
}
