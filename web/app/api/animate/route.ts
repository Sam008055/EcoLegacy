import { NextResponse } from 'next/server';
import { getErrorMessage, isValidAudioUrl } from '@/utils/errorMessage';

function isNgrokConfigured(url: string | undefined): boolean {
  if (!url || url.trim() === '') return false
  const lower = url.toLowerCase()
  if (lower.includes('placeholder')) return false
  return lower.startsWith('http')
}

export async function POST(req: Request) {
  try {
    const { audioUrl } = await req.json();

    if (!audioUrl) {
      return NextResponse.json({ error: 'Audio URL is required' }, { status: 400 });
    }

    if (!isValidAudioUrl(audioUrl)) {
      return NextResponse.json({
        videoUrl: null,
        message: 'Invalid or empty audio — video animation skipped.',
      });
    }

    console.log('[Animate] Requesting animation for audio:', audioUrl.slice(0, 80) + '...');
    
    const ngrokUrl = process.env.NGROK_URL;

    if (!isNgrokConfigured(ngrokUrl)) {
      console.warn('[Animate] NGROK_URL not configured (or placeholder). Skipping video.');
      return NextResponse.json({ 
        videoUrl: null, 
        message: 'No Wav2Lip server configured. Video animation skipped.' 
      });
    }

    // Call the external Ngrok Wav2Lip server
    const animateRes = await fetch(`${ngrokUrl}/animate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        audio_url: audioUrl,
      })
    });

    if (!animateRes.ok) {
      console.warn(`[Animate] Ngrok server responded with status: ${animateRes.status}`);
      return NextResponse.json({
        videoUrl: null,
        message: `Wav2Lip server unavailable (${animateRes.status}). Playing audio only.`,
      });
    }

    const data = await animateRes.json();
    
    const videoUrl = data.video_url || data.videoUrl;

    if (!videoUrl) {
      return NextResponse.json({
        videoUrl: null,
        message: 'Video URL not found in Wav2Lip response.',
      });
    }

    console.log('[Animate] Animation successful, video URL:', videoUrl);
    return NextResponse.json({ videoUrl });

  } catch (error: unknown) {
    console.error('[Animate] API Error:', error);
    return NextResponse.json({
      videoUrl: null,
      message: getErrorMessage(error) || 'Animation Failed',
    });
  }
}
