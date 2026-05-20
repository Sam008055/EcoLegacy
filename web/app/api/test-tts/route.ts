import { NextResponse } from 'next/server';

export async function GET() {
  const localTtsUrl = process.env.LOCAL_TTS_URL || 'http://127.0.0.1:5000';
  
  console.log('[DEBUG] LOCAL_TTS_URL from env:', process.env.LOCAL_TTS_URL);
  console.log('[DEBUG] Using URL:', localTtsUrl);
  
  try {
    // Test health endpoint first
    console.log('[DEBUG] Testing health endpoint...');
    const healthResponse = await fetch(`${localTtsUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    
    console.log('[DEBUG] Health response status:', healthResponse.status);
    const healthData = await healthResponse.json();
    console.log('[DEBUG] Health data:', healthData);
    
    // Test TTS endpoint
    console.log('[DEBUG] Testing TTS endpoint...');
    const ttsResponse = await fetch(`${localTtsUrl}/tts`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'audio/wav'
      },
      body: JSON.stringify({
        text: 'Hello debug test',
        character_id: 'osho'
      }),
      signal: AbortSignal.timeout(10000)
    });
    
    console.log('[DEBUG] TTS response status:', ttsResponse.status);
    console.log('[DEBUG] TTS response headers:', Object.fromEntries(ttsResponse.headers.entries()));
    
    if (ttsResponse.ok) {
      const audioBlob = await ttsResponse.blob();
      console.log('[DEBUG] Audio blob size:', audioBlob.size);
      
      return NextResponse.json({
        success: true,
        health: healthData,
        tts: {
          status: ttsResponse.status,
          audioSize: audioBlob.size,
          contentType: ttsResponse.headers.get('content-type')
        }
      });
    } else {
      const errorText = await ttsResponse.text();
      console.log('[DEBUG] TTS error:', errorText);
      
      return NextResponse.json({
        success: false,
        health: healthData,
        tts: {
          status: ttsResponse.status,
          error: errorText
        }
      });
    }
    
  } catch (error: any) {
    console.error('[DEBUG] Connection error:', error);
    
    return NextResponse.json({
      success: false,
      error: error.message,
      url: localTtsUrl,
      env: process.env.LOCAL_TTS_URL
    }, { status: 500 });
  }
}