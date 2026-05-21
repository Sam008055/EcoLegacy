import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import Groq from 'groq-sdk';
import { characters, CharacterId } from '@/utils/characters';

// Simple embedding function using OpenAI-compatible API
async function generateEmbedding(text: string): Promise<number[]> {
  try {
    // Use a simple sentence transformer approach via Groq
    const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });
    
    // Generate a simple hash-based embedding for now
    const normalized = text.toLowerCase().trim();
    const embedding = new Array(384).fill(0);
    
    // Simple hash-based embedding (temporary solution)
    for (let i = 0; i < normalized.length; i++) {
      const char = normalized.charCodeAt(i);
      embedding[i % 384] += char;
    }
    
    // Normalize the embedding
    const magnitude = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
    return embedding.map(val => val / magnitude);
  } catch (error) {
    console.error('[CHAT] Embedding generation failed:', error);
    // Return a zero vector as fallback
    return new Array(384).fill(0);
  }
}

export async function POST(req: Request) {
  try {
    console.log('[CHAT] API called');
    
    const { query, characterId, userEmail } = await req.json();
    console.log('[CHAT] Request data:', { query: query?.substring(0, 50), characterId, userEmail });

    if (!query) {
      return NextResponse.json({ error: 'Query is required' }, { status: 400 });
    }

    const character = characters[characterId as CharacterId] || characters.osho;
    console.log('[CHAT] Character selected:', character.name);

    // Check environment variables
    const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    const groqKey = process.env.GROQ_API_KEY;

    console.log('[CHAT] Environment check:', {
      supabaseUrl: supabaseUrl ? 'SET' : 'MISSING',
      supabaseKey: supabaseKey ? 'SET' : 'MISSING', 
      groqKey: groqKey ? 'SET' : 'MISSING'
    });

    if (!supabaseUrl || !supabaseKey) {
      console.error('[CHAT] Missing Supabase credentials');
      return NextResponse.json({ error: 'Supabase configuration missing' }, { status: 500 });
    }

    if (!groqKey) {
      console.error('[CHAT] Missing Groq API key');
      return NextResponse.json({ error: 'Groq API key missing' }, { status: 500 });
    }

    const supabase = createClient(supabaseUrl, supabaseKey);
    console.log('[CHAT] Supabase client created');

    let interactionsCount = 0;
    const ADMIN_EMAIL = 'samarthpasalkar4@gmail.com';
    const isAdmin = userEmail === ADMIN_EMAIL;

    // RATE LIMITING LOGIC - STRICT ENFORCEMENT
    if (userEmail && !isAdmin) {
      try {
        // Check existing conversations for this user - USE SERVICE ROLE KEY
        const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL!;
        const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY!; // Always use service role key
        const rateLimitSupabase = createClient(supabaseUrl, supabaseKey);

        const { data: existingConvos, error: convoError } = await rateLimitSupabase
          .from('conversations')
          .select('character_id, created_at')
          .eq('session_id', userEmail)
          .order('created_at', { ascending: true });

        if (convoError) {
          console.error('[CHAT] Supabase conversation query error:', JSON.stringify(convoError, null, 2));
          console.error('[CHAT] Supabase URL:', supabaseUrl ? 'SET' : 'MISSING');
          console.error('[CHAT] Supabase Key:', supabaseKey ? 'SET' : 'MISSING');
          
          // Check if it's a specific database error we can handle
          if (convoError.code === 'PGRST116' || convoError.message?.includes('relation') || convoError.message?.includes('does not exist')) {
            console.log('[CHAT] Table does not exist, allowing request to continue');
            // Table doesn't exist yet, allow the request (first time setup)
          } else {
            // Other database errors - block to prevent abuse
            return NextResponse.json({ 
              error: 'SERVICE_UNAVAILABLE', 
              message: 'Service temporarily unavailable. Please try again later.',
              details: convoError.message 
            }, { status: 503 });
          }
        }

        const convos = existingConvos || [];
        console.log(`[CHAT] User ${userEmail} has ${convos.length} existing conversations`);

        // 1. Check if user is trying a different character than their first one
        if (convos.length > 0) {
          const firstCharacter = convos[0].character_id;
          if (firstCharacter !== characterId) {
            console.log(`[CHAT] Character locked for ${userEmail}. Locked to: ${firstCharacter}, tried: ${characterId}`);
            return NextResponse.json({ 
              error: 'CHARACTER_LOCKED', 
              message: `You can only interact with one character. You're locked to your first choice: ${firstCharacter}`,
              lockedCharacter: firstCharacter
            }, { status: 403 });
          }
        }

        // 2. STRICT: Check if user has used up their 2 free queries
        if (convos.length >= 2) {
          console.log(`[CHAT] RATE LIMIT ENFORCED for ${userEmail}. Count: ${convos.length}`);
          return NextResponse.json({ 
            error: 'RATE_LIMIT_REACHED', 
            message: 'You have reached the maximum of 2 free interactions. Please share your feedback to help us improve!' 
          }, { status: 429 });
        }
        
        interactionsCount = convos.length + 1; // Including the current query
        console.log(`[CHAT] User ${userEmail} interaction ${interactionsCount}/2`);

      } catch (dbError: any) {
        console.error('[CHAT] Database connection error:', JSON.stringify(dbError, null, 2));
        console.error('[CHAT] Error message:', dbError.message);
        console.error('[CHAT] Error code:', dbError.code);
        
        // Check if it's a table/schema issue we can handle
        if (dbError.message?.includes('relation') || dbError.message?.includes('does not exist') || dbError.code === 'PGRST116') {
          console.log('[CHAT] Database schema issue, allowing request to continue');
          // Allow the request to continue for first-time setup
        } else {
          // Other connection errors - block to prevent abuse
          return NextResponse.json({ 
            error: 'SERVICE_UNAVAILABLE', 
            message: 'Service temporarily unavailable. Please try again later.',
            details: dbError.message 
          }, { status: 503 });
        }
      }
    }

    console.log('[CHAT] Checking cache for quick response...');
    let cachedResponse = null;
    let cacheError = null;
    
    try {
      // Use service role key for cache queries too
      const cacheSupabase = createClient(supabaseUrl, process.env.SUPABASE_SERVICE_ROLE_KEY!);
      const cacheResult = await cacheSupabase
        .from('cached_responses')
        .select('*')
        .eq('character_id', characterId)
        .eq('question', query.trim().toLowerCase())
        .single();
      
      cachedResponse = cacheResult.data;
      cacheError = cacheResult.error;
    } catch (err) {
      console.warn('[CHAT] Cache query failed:', err);
      cacheError = err;
    }

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

    // Generate embedding and search for context
    console.log('[CHAT] Cache miss. Generating embedding...');
    const queryEmbedding = await generateEmbedding(query);
    
    console.log(`[CHAT] Searching for context (${character.name})...`);
    let contextChunks = null;
    let supabaseError = null;
    
    try {
      // Use service role key for RAG queries too
      const ragSupabase = createClient(supabaseUrl, process.env.SUPABASE_SERVICE_ROLE_KEY!);
      const contextResult = await ragSupabase.rpc('match_documents', {
        query_embedding: queryEmbedding,
        match_threshold: 0.2,
        match_count: 2,
        p_character_id: character.id
      });
      
      contextChunks = contextResult.data;
      supabaseError = contextResult.error;
    } catch (err) {
      console.warn('[CHAT] Context search failed:', err);
      supabaseError = err;
    }

    if (supabaseError) {
      console.error('[CHAT] Supabase Error:', supabaseError);
      // Continue without context if RAG fails
    }

    let contextText = 'No specific context available.';
    if (contextChunks && contextChunks.length > 0) {
      contextText = contextChunks[0].content;
    }

    console.log(`[CHAT] Generating response...`);
    const groq = new Groq({
      apiKey: groqKey,
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
      max_tokens: 50,
      temperature: 0.7,
    });

    const responseText = chatCompletion.choices[0]?.message?.content || 'I have no response right now.';
    console.log('[CHAT] Generated text:', responseText);

    // Cache the response for future use (async, don't wait)
    if (responseText) {
      try {
        const cacheSupabase = createClient(supabaseUrl, process.env.SUPABASE_SERVICE_ROLE_KEY!);
        cacheSupabase.from('cached_responses').insert({
          character_id: characterId,
          question: query.trim().toLowerCase(),
          answer_text: responseText
        }).then(({ error }) => {
          if (error) console.warn('[CHAT] Failed to cache response:', error);
          else console.log('[CHAT] Response cached for future use');
        });
      } catch (err) {
        console.warn('[CHAT] Cache insert failed:', err);
      }
    }

    // Log conversation to track usage - CRITICAL for rate limiting
    if (userEmail) {
      try {
        const logSupabase = createClient(supabaseUrl, process.env.SUPABASE_SERVICE_ROLE_KEY!);
        console.log(`[CHAT] Logging conversation for ${userEmail} with character ${characterId}`);
        
        const { data, error } = await logSupabase.from('conversations').insert({
          session_id: userEmail,
          character_id: characterId,
          user_message: query,
          avatar_response: responseText
        });
        
        if (error) {
          console.error('[CHAT] CRITICAL: Failed to log conversation:', JSON.stringify(error, null, 2));
          console.error('[CHAT] This will break rate limiting!');
        } else {
          console.log('[CHAT] ✅ Conversation logged successfully for rate limiting');
        }
      } catch (err) {
        console.error('[CHAT] CRITICAL: Conversation logging exception:', err);
      }
    }

    return NextResponse.json({ 
      text: responseText,
      cached: false,
      source: 'generated',
      interactionsCount,
      isAdmin
    });

  } catch (error: any) {
    console.error('[CHAT] API Error:', error);
    console.error('[CHAT] Error stack:', error.stack);
    return NextResponse.json({ 
      error: error.message || 'Internal Server Error',
      details: error.stack?.split('\n')[0] || 'Unknown error'
    }, { status: 500 });
  }
}
