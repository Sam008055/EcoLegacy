import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import fs from 'fs';
import { characters, CharacterId } from '@/utils/characters';
import { getErrorMessage, isValidAudioUrl } from '@/utils/errorMessage';
import { getReferenceAudioPath } from '@/utils/referenceAudioPath';
import { extractGradioAudioPath } from '@/utils/gradioAudio';

const HF_SPACE = 'chenxie95/Cross-Lingual_F5-TTS_Space';
const SMALLEST_API_BASE = 'https://api.smallest.ai/waves/v1';

// Store voice IDs for each character (pre-created voice clones)
const CHARACTER_VOICE_IDS: Record<string, string> = {
  osho: 'osho_voice_clone_id', // Replace with actual voice ID from smallest.ai
  bhagat_singh: 'bhagat_voice_clone_id',
  ssr: 'ssr_voice_clone_id', 
  tesla: 'tesla_voice_clone_id',
  hitler: 'hitler_voice_clone_id'
};

function getHfTokens(): string[] {
  return [
    process.env.HUGGINGFACE_TOKEN,
    process.env.HUGGINGFACE_TOKEN_1,
    process.env.HUGGINGFACE_TOKEN_2,
    process.env.HUGGINGFACE_TOKEN_3,
    process.env.HUGGINGFACE_TOKEN_4,
    process.env.HUGGINGFACE_TOKEN_5,
    process.env.HUGGINGFACE_TOKEN_6,
    process.env.HUGGINGFACE_TOKEN_7,
    process.env.HUGGINGFACE_TOKEN_8,
    process.env.HUGGINGFACE_TOKEN_9,
  ].filter(Boolean) as string[];
}

/** Create voice clone using smallest.ai API */
async function createVoiceClone(
  characterId: CharacterId,
  referenceAudioPath: string,
): Promise<string | null> {
  const apiKey = process.env.SMALLEST_API_KEY;
  if (!apiKey) {
    console.error('[TTS] No SMALLEST_API_KEY configured');
    return null;
  }

  try {
    const formData = new FormData();
    const audioBuffer = fs.readFileSync(referenceAudioPath);
    const audioBlob = new Blob([audioBuffer], { type: 'audio/mpeg' });

    formData.append('file', audioBlob, `${characterId}_ref.mp3`);
    formData.append('displayName', `${characterId.charAt(0).toUpperCase() + characterId.slice(1)} Voice Clone`);
    formData.append('description', `Voice clone for ${characterId} character`);
    formData.append('model', 'lightning-v3.1');
    formData.append('language', 'en');

    console.log(`[TTS] Creating voice clone for ${characterId} using smallest.ai`);
    console.log(`[TTS] Reference audio: ${referenceAudioPath}`);
    console.log(`[TTS] Audio file size: ${audioBuffer.length} bytes`);
    console.log(`[TTS] API Key configured: ${apiKey ? 'Yes' : 'No'}`);

    const response = await fetch(`${SMALLEST_API_BASE}/voice-cloning`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
      },
      body: formData,
    });

    console.log(`[TTS] Smallest.ai response status: ${response.status}`);

    if (response.ok) {
      const result = await response.json();
      console.log(`[TTS] Smallest.ai response:`, JSON.stringify(result, null, 2));
      const voiceId = result.data?.voiceId;
      if (voiceId) {
        CHARACTER_VOICE_IDS[characterId] = voiceId;
        console.log(`[TTS] Voice clone created successfully: ${voiceId}`);
        return voiceId;
      } else {
        console.error('[TTS] No voiceId in response:', result);
        return null;
      }
    } else {
      const errorText = await response.text();
      console.error(`[TTS] Voice clone creation failed: ${response.status} - ${errorText}`);
      return null;
    }
  } catch (error) {
    console.error('[TTS] Error creating voice clone:', error);
    return null;
  }
}

/** Generate speech using smallest.ai TTS */
async function generateWithSmallestAI(
  text: string,
  characterId: CharacterId,
  referenceAudioPath: string,
): Promise<{ audioUrl: string; source: string }> {
  const apiKey = process.env.SMALLEST_API_KEY;
  if (!apiKey) {
    throw new Error('SMALLEST_API_KEY not configured in environment');
  }

  // Use pre-created voice ID or create new one
  let voiceId: string | null = CHARACTER_VOICE_IDS[characterId] || null;
  
  // If no pre-created voice ID, create one (but this should be done once manually)
  if (!voiceId || voiceId.includes('_clone_id')) {
    console.log(`[TTS] No pre-created voice ID for ${characterId}, creating new one...`);
    voiceId = await createVoiceClone(characterId, referenceAudioPath);
    if (!voiceId) {
      throw new Error(`Failed to create voice clone for ${characterId}`);
    }
  }

  try {
    console.log(`[TTS] Generating speech with smallest.ai voice ${voiceId}`);

    const response = await fetch(`${SMALLEST_API_BASE}/lightning-v3.1/get_speech`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: text,
        voice_id: voiceId,
        speed: 1.0,
        sample_rate: 24000,
        output_format: 'wav',
      }),
    });

    if (response.ok) {
      // Direct audio response
      const audioBuffer = await response.arrayBuffer();
      const base64Audio = Buffer.from(audioBuffer).toString('base64');
      const audioUrl = `data:audio/wav;base64,${base64Audio}`;
      console.log(`[TTS] Speech generated successfully (${audioBuffer.byteLength} bytes)`);
      return { audioUrl, source: 'smallest-ai' };
    } else {
      const errorText = await response.text();
      throw new Error(`Smallest.ai TTS failed: ${response.status} - ${errorText}`);
    }
  } catch (error) {
    console.error('[TTS] Smallest.ai generation error:', error);
    throw error;
  }
}

/** Voice clone using ONLY the character reference clip in web/public/audio. */
async function generateWithReferenceVoice(
  text: string,
  characterId: CharacterId,
  referenceAudioPath: string,
): Promise<{ audioUrl: string; tokenIndex: number }> {
  const hfTokens = getHfTokens();
  if (hfTokens.length === 0) {
    throw new Error('No HUGGINGFACE_TOKEN configured in .env.local');
  }

  const { Client, handle_file } = await import('@gradio/client');
  let lastError: unknown = null;

  for (let i = 0; i < hfTokens.length; i++) {
    const token = hfTokens[i];
    try {
      console.log(`[TTS] Reference clone HF token ${i + 1}/${hfTokens.length} | ref=${referenceAudioPath}`);

      const gradioClient = await Client.connect(HF_SPACE, { hf_token: token } as any);

      const character = characters[characterId];
      const result = await gradioClient.predict('/basic_tts', {
        ref_wav_input: handle_file(referenceAudioPath),
        ref_text_input: character.referenceText || '',
        gen_txt_input: text,
        randomize_seed: true,
        seed_input: 0,
      });

      const audioPath = extractGradioAudioPath(result);
      if (audioPath) {
        console.log(`[TTS] Reference clone OK (token ${i + 1}):`, audioPath);
        return { audioUrl: audioPath, tokenIndex: i };
      }

      console.warn(`[TTS] Token ${i + 1}: HF returned no audio path`, result);
    } catch (err: unknown) {
      lastError = err;
      console.error(`[TTS] Token ${i + 1} failed:`, getErrorMessage(err));
    }
  }

  const msg = getErrorMessage(lastError);
  if (msg.includes('quota') || msg.includes('ZeroGPU')) {
    throw new Error(
      'HuggingFace ZeroGPU quota exceeded. Start minimal_tts_server.py or wait for quota reset.'
    );
  }
  throw new Error(`Reference voice clone failed: ${msg || 'unknown error'}`);
}

export async function POST(req: Request) {
  try {
    const { text, characterId, userEmail } = await req.json();

    if (!text) {
      return NextResponse.json({ error: 'Text is required' }, { status: 400 });
    }

    const id = (characterId as CharacterId) in characters ? (characterId as CharacterId) : 'osho';
    const character = characters[id];

    // RATE LIMITING FOR TTS - Prevent direct API abuse
    if (userEmail && userEmail !== 'samarthpasalkar4@gmail.com') {
      const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!;
      const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
      const supabase = createClient(supabaseUrl, supabaseKey);

      const { data: existingConvos } = await supabase
        .from('conversations')
        .select('character_id')
        .eq('session_id', userEmail);

      const convos = existingConvos || [];
      if (convos.length >= 2) {
        console.log(`[TTS] Rate limit enforced for ${userEmail}. Conversations: ${convos.length}`);
        return NextResponse.json({ 
          error: 'RATE_LIMIT_REACHED', 
          message: 'You have reached the maximum of 2 free interactions. Please share your feedback!' 
        }, { status: 429 });
      }
    }

    const referenceAudioPath = getReferenceAudioPath(id);
    if (!fs.existsSync(referenceAudioPath)) {
      return NextResponse.json(
        {
          error: `Reference audio missing for ${id}`,
          path: referenceAudioPath,
          hint: `Add ${character.referenceAudio} under web/public/audio/`,
        },
        { status: 400 },
      );
    }

    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey =
      process.env.SUPABASE_SERVICE_ROLE_KEY ||
      process.env.SUPABASE_ANON_KEY ||
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    const cacheKey = `${id}_${text.trim().toLowerCase()}`;

    console.log(`[TTS] Checking cache for: ${cacheKey.slice(0, 50)}...`);

    const { data: cachedAudio, error: cacheError } = await supabase
      .from('audio_cache')
      .select('audio_url')
      .eq('cache_key', cacheKey)
      .single();

    if (cachedAudio && !cacheError && isValidAudioUrl(cachedAudio.audio_url)) {
      console.log('[TTS] Cache hit');
      return NextResponse.json({ audioUrl: cachedAudio.audio_url, cached: true, source: 'cache' });
    }
    if (cachedAudio && !isValidAudioUrl(cachedAudio.audio_url)) {
      await supabase.from('audio_cache').delete().eq('cache_key', cacheKey);
    }

    console.log(`[TTS] Cloning ${character.name} voice from ${character.referenceAudio}`);

    // Try smallest.ai first (primary method)
    if (process.env.SMALLEST_API_KEY) {
      try {
        const { audioUrl, source } = await generateWithSmallestAI(text, id, referenceAudioPath);

        // Cache the result
        try {
          await supabase.from('audio_cache').insert({
            cache_key: cacheKey,
            character_id: id,
            text,
            audio_url: audioUrl,
            successful_token_index: -1,
          });
        } catch {
          /* cache optional */
        }

        return NextResponse.json({
          audioUrl,
          cached: false,
          source,
          referenceFile: character.referenceAudio,
        });
      } catch (error) {
        console.warn('[TTS] Smallest.ai failed, trying fallback:', getErrorMessage(error));
      }
    } else {
      console.log('[TTS] SMALLEST_API_KEY not configured, skipping smallest.ai');
    }

    // Fallback to local Python server
    const localTtsUrl = process.env.LOCAL_TTS_URL;
    if (localTtsUrl) {
      try {
        const localTimeoutMs = Number(process.env.LOCAL_TTS_TIMEOUT_MS || 120000);
        const localRes = await fetch(`${localTtsUrl}/tts`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'audio/wav' },
          body: JSON.stringify({ text, character_id: id }),
          signal: AbortSignal.timeout(localTimeoutMs),
        });

        if (localRes.ok && !localRes.headers.get('content-type')?.includes('application/json')) {
          const blob = await localRes.blob();
          if (blob.size >= 100) {
            const base64 = Buffer.from(await blob.arrayBuffer()).toString('base64');
            const audioUrl = `data:audio/wav;base64,${base64}`;
            try {
              await supabase.from('audio_cache').insert({
                cache_key: cacheKey,
                character_id: id,
                text,
                audio_url: audioUrl,
                successful_token_index: -1,
              });
            } catch (cacheErr) {
              console.warn('[TTS] Failed to cache local response:', cacheErr);
            }
            return NextResponse.json({ audioUrl, cached: false, source: 'local-reference' });
          }
        }
        const errJson = await localRes.json().catch(() => ({}));
        console.warn('[TTS] Local reference server failed:', localRes.status, errJson);
      } catch (e) {
        console.warn('[TTS] Local server unreachable:', getErrorMessage(e));
      }
    }

    // Final fallback to HuggingFace (if quota available)
    const { audioUrl, tokenIndex } = await generateWithReferenceVoice(text, id, referenceAudioPath);

    try {
      await supabase.from('audio_cache').insert({
        cache_key: cacheKey,
        character_id: id,
        text,
        audio_url: audioUrl,
        successful_token_index: tokenIndex,
      });
    } catch {
      /* cache optional */
    }

    return NextResponse.json({
      audioUrl,
      cached: false,
      source: 'huggingface-fallback',
      referenceFile: character.referenceAudio,
    });
  } catch (error: unknown) {
    console.error('[TTS] API Error:', error);
    return NextResponse.json(
      { error: getErrorMessage(error) || 'TTS generation failed' },
      { status: 500 },
    );
  }
}
