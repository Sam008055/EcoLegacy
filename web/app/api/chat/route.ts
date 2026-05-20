import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import Groq from 'groq-sdk';
import { pipeline, env } from '@xenova/transformers';
import { characters, CharacterId } from '@/utils/characters';

// Configure transformers to not look for local models in the node_modules directory
env.allowLocalModels = false;
env.useBrowserCache = false;

// We can instantiate these outside the handler to reuse them across requests (if the runtime allows)
let embeddingPipeline: any = null;

export async function POST(req: Request) {
  try {
    const { query, characterId, userEmail } = await req.json();

    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    const character = characters[characterId as CharacterId] || characters.osho;

    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
    const supabase = createClient(supabaseUrl, supabaseKey);

    let interactionsCount = 0;
    const ADMIN_EMAIL = 'samarthpasalkar4@gmail.com';
    const isAdmin = userEmail === ADMIN_EMAIL;

    // RATE LIMITING LOGIC
    if (userEmail && !isAdmin) {
      // Check existing conversations for this user
      const { data: existingConvos } = await supabase
        .from('conversations')
        .select('character_id')
        .eq('session_id', userEmail);

      const convos = existingConvos || [];

      // 1. Check if user is trying a different character than their first one
      if (convos.length > 0) {
        const firstCharacter = convos[0].character_id;
        if (firstCharacter !== characterId) {
          console.log(`[CHAT] Character locked for ${userEmail}. Locked to: ${firstCharacter}, tried: ${characterId}`);
          return NextResponse.json({ 
            error: 'CHARACTER_LOCKED', 
            message: `You can only interact with one character. You're locked to your first choice.`,
            lockedCharacter: firstCharacter
          }, { status: 403 });
        }
      }

      // 2. Check if user has used up their 2 free queries
      if (convos.length >= 2) {
        console.log(`[CHAT] Rate limit reached for ${userEmail}. Count: ${convos.length}`);
        return NextResponse.json({ 
          error: 'RATE_LIMIT_REACHED', 
          message: 'You have reached the maximum of 2 free interactions. Please share your feedback!' 
        }, { status: 429 });
      }
      
      interactionsCount = convos.length + 1; // Including the current query
    }

    console.log('[CHAT] Checking cache for quick response...');
    const { data: cachedResponse, error: cacheError } = await supabase
      .from('cached_responses')
      .select('*')
      .eq('character_id', characterId)
      .eq('question', query.trim().toLowerCase())
      .single();

    if (cachedResponse && !cacheError) {
      console.log('[CHAT] Cache hit! Returning cached response');
      return NextResponse.json({ 
        text: cachedResponse.answer_text,
        cached: true,
        source: 'cache',
        interactionsCount,
        isAdmin
      });
    }

    // 1. Generate Embedding (optimized)
    console.log('[CHAT] Cache miss. Generating embedding...');
    if (!embeddingPipeline) {
      embeddingPipeline = await pipeline('feature-extraction', 'Xenova/all-mpnet-base-v2');
    }
    
    // Perform embedding
    const output = await embeddingPipeline(query, { pooling: 'mean', normalize: true });
    const queryEmbedding = Array.from(output.data);

    // 2. Query Supabase (RAG) - Optimized for speed
    console.log(`[CHAT] Searching for context (${character.name})...`);

    const { data: contextChunks, error: supabaseError } = await supabase.rpc('match_documents', {
      query_embedding: queryEmbedding,
      match_threshold: 0.2, // Lower threshold for faster results
      match_count: 2, // Reduced from 3 to 2 for speed
      p_character_id: character.id
    });

    if (supabaseError) {
      console.error('Supabase Error:', supabaseError);
      throw supabaseError;
    }

    let contextText = 'No specific context available.';
    if (contextChunks && contextChunks.length > 0) {
      // Take only the most relevant chunk for speed
      contextText = contextChunks[0].content;
    }

    // 3. Generate Text with Groq (optimized prompt)
    console.log(`[CHAT] Generating response...`);
    const groq = new Groq({
      apiKey: process.env.GROQ_API_KEY,
    });

    const systemPrompt = `${character.systemPrompt}

CRITICAL: Keep responses EXTREMELY short - maximum 15 words. Be direct and conversational.

Context (use only if directly relevant):
${contextText}`;

    const chatCompletion = await groq.chat.completions.create({
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: query }
      ],
      model: 'llama-3.1-8b-instant',
      max_tokens: 50, // Reduced from default for shorter responses
      temperature: 0.7,
    });

    const responseText = chatCompletion.choices[0]?.message?.content || 'I have no response right now.';
    console.log('[CHAT] Generated text:', responseText);

    // Cache the response for future use (async, don't wait)
    supabase.from('cached_responses').insert({
      character_id: characterId,
      question: query.trim().toLowerCase(),
      answer_text: responseText
    }).then(({ error }) => {
      if (error) console.warn('[CHAT] Failed to cache response:', error);
      else console.log('[CHAT] Response cached for future use');
    });

    // Log conversation to track usage
    if (userEmail) {
      supabase.from('conversations').insert({
        session_id: userEmail,
        character_id: characterId,
        user_message: query,
        avatar_response: responseText
      }).then(({ error }) => {
        if (error) console.warn('[CHAT] Failed to log conversation:', error);
      });
    }

    return NextResponse.json({ 
      text: responseText,
      cached: false,
      source: 'generated',
      interactionsCount,
      isAdmin
    });

  } catch (error: any) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}
