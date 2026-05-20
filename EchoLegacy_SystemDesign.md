# EchoLegacy — System Design Document

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    BROWSER (Next.js)                     │
│                                                          │
│  [Mic Button] → Web Speech API → transcript text        │
│                                                          │
│  [Osho Portrait]  ← LivePortrait video stream            │
│  [Audio Player]   ← Fish.audio MP3                      │
│  [Text Display]   ← Gemini response                     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTPS API calls
┌────────────────────────▼────────────────────────────────┐
│                  Next.js API Routes                      │
│                                                          │
│  /api/chat      → RAG + Gemini pipeline                 │
│  /api/speak     → Fish.audio TTS                        │
│  /api/animate   → Ngrok → LivePortrait local server     │
└──────┬──────────────────┬──────────────────┬────────────┘
       │                  │                  │
┌──────▼──────┐  ┌────────▼──────┐  ┌───────▼────────────┐
│  Supabase   │  │  Gemini API   │  │   Fish.audio API   │
│  pgvector   │  │  Flash + Emb  │  │   Osho voice       │
│  RAG store  │  │  Free tier    │  │   8000 credits     │
└─────────────┘  └───────────────┘  └────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │   Ngrok Tunnel     │
                                    │   → localhost:7860 │
                                    │   LivePortrait     │
                                    │   RTX 3050 4GB     │
                                    └────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Firebase                              │
│  - Conversation history (Realtime DB)                   │
│  - Cached audio files (Storage)                         │
│  - Session analytics                                    │
└─────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Voice Input
```javascript
// Web Speech API — zero cost, Chrome native
const recognition = new webkitSpeechRecognition()
recognition.continuous = false
recognition.lang = 'en-IN' // Indian English accent optimized (Osho spoke in English)
recognition.onresult = (e) => {
  const transcript = e.results[0][0].transcript
  sendToChat(transcript)
}
```

### 2. RAG Pipeline — /api/chat

```
Step 1: Embed user query
  → POST to Gemini embedding API
  → model: "text-embedding-004"
  → returns 768-dim vector

Step 2: Vector search Supabase
  → match_documents(query_embedding, threshold=0.7, count=5)
  → returns top 5 Osho text chunks

Step 3: Build context prompt
  → System: Osho master persona prompt
  → Context: 5 retrieved passages
  → User: query

Step 4: Gemini Flash generate
  → model: gemini-1.5-flash
  → max_tokens: 200 (keep responses short for TTS)
  → returns Osho's response text

Step 5: Return text to frontend
```

### 3. Supabase Schema

```sql
-- Enable pgvector
create extension if not exists vector;

-- Osho corpus chunks
create table osho_corpus (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  source text, -- "The Book of Secrets", "Courage" etc
  chapter text,
  embedding vector(768),
  created_at timestamp default now()
);

-- Vector similarity search function
create or replace function match_documents(
  query_embedding vector(768),
  match_threshold float default 0.7,
  match_count int default 5
)
returns table(id uuid, content text, source text, similarity float)
language sql stable
as $$
  select
    id, content, source,
    1 - (embedding <=> query_embedding) as similarity
  from osho_corpus
  where 1 - (embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
$$;

-- Conversation logs
create table conversations (
  id uuid primary key default gen_random_uuid(),
  session_id text,
  user_message text,
  kalam_response text,
  audio_url text,
  created_at timestamp default now()
);
```

### 4. RAG Ingestion Script

```javascript
// run once to populate Supabase
// scripts/ingest.js

import { createClient } from '@supabase/supabase-js'
import { GoogleGenerativeAI } from '@google/generative-ai'
import fs from 'fs'

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)
const genAI = new GoogleGenerativeAI(GEMINI_KEY)

async function ingestText(text, source) {
  // chunk into ~500 token pieces with 50 token overlap
  const chunks = chunkText(text, 500, 50)
  
  for (const chunk of chunks) {
    // embed with Gemini
    const model = genAI.getGenerativeModel({ model: "text-embedding-004" })
    const result = await model.embedContent(chunk)
    const embedding = result.embedding.values
    
    // store in Supabase
    await supabase.from('kalam_corpus').insert({
      content: chunk,
      source: source,
      embedding: embedding
    })
  }
}

// Ingest all sources
await ingestText(fs.readFileSync('corpus/book-of-secrets.txt', 'utf8'), 'The Book of Secrets')
await ingestText(fs.readFileSync('corpus/courage.txt', 'utf8'), 'Courage')
await ingestText(fs.readFileSync('corpus/discourses.txt', 'utf8'), 'Discourses')
```

### 5. Fish.audio Integration — /api/speak

```javascript
// POST /api/speak
export async function POST(req) {
  const { text } = await req.json()
  
  // Check Firebase cache first
  const cached = await checkAudioCache(text)
  if (cached) return Response.json({ audioUrl: cached })
  
  // Generate with Fish.audio
  const response = await fetch('https://api.fish.audio/v1/tts', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.FISH_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: text,
      reference_id: process.env.KALAM_VOICE_ID, // Kalam model ID from fish.audio
      format: 'mp3',
      streaming: false
    })
  })
  
  const audioBuffer = await response.arrayBuffer()
  
  // Cache to Firebase Storage
  const audioUrl = await cacheToFirebase(audioBuffer, text)
  
  return Response.json({ audioUrl })
}
```

### 6. LivePortrait Integration — /api/animate

```javascript
// POST /api/animate
// Calls local LivePortrait server via Ngrok
export async function POST(req) {
  const { audioUrl } = await req.json()
  
  try {
    const response = await fetch(`${process.env.NGROK_URL}/animate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_image: 'kalam_portrait.jpg', // stored locally on GPU machine
        audio_url: audioUrl,
      }),
      signal: AbortSignal.timeout(15000) // 15s timeout
    })
    
    const { video_url } = await response.json()
    return Response.json({ videoUrl: video_url })
    
  } catch (error) {
    // Fallback: return null, frontend shows static photo + audio
    return Response.json({ videoUrl: null })
  }
}
```

### 7. Firebase Structure

```
Firebase Realtime DB:
  sessions/
    {sessionId}/
      startTime: timestamp
      messages: []
      messageCount: number

Firebase Storage:
  audio-cache/
    {md5_of_text}.mp3   ← cached Fish.audio responses
  videos/
    {md5_of_text}.mp4   ← cached LivePortrait animations
```

---

## Latency Budget

| Step | Target Time |
|------|-------------|
| STT (Web Speech) | ~1s |
| Gemini embed | ~0.5s |
| Supabase vector search | ~0.3s |
| Gemini Flash generate | ~1.5s |
| Fish.audio TTS | ~2s |
| LivePortrait animate | ~4s |
| **Total** | **~9s** |

Cache hits skip steps 4-6, bringing latency to ~2s.

---

## Environment Variables

```bash
# .env.local
GEMINI_API_KEY=
FISH_API_KEY=
OSHO_VOICE_ID=your_osho_voice_model_id_here
SUPABASE_URL=
SUPABASE_ANON_KEY=
FIREBASE_API_KEY=
FIREBASE_PROJECT_ID=
NGROK_URL=https://xxxx.ngrok-free.app
```

---

## Folder Structure

```
echolegacy/
├── app/
│   ├── page.jsx              # Main UI
│   ├── layout.jsx
│   └── api/
│       ├── chat/route.js     # RAG + Gemini
│       ├── speak/route.js    # Fish.audio TTS
│       └── animate/route.js  # LivePortrait via Ngrok
├── components/
│   ├── OshoPortrait.jsx      # Video/image display
│   ├── VoiceInput.jsx        # Mic button + Web Speech
│   ├── ChatHistory.jsx       # Conversation display
│   └── AudioPlayer.jsx       # Hidden audio element
├── lib/
│   ├── gemini.js             # Gemini client
│   ├── supabase.js           # Supabase client
│   ├── firebase.js           # Firebase client
│   └── fishAudio.js          # Fish.audio client
├── scripts/
│   └── ingest.js             # RAG corpus ingestion
├── corpus/
│   ├── book-of-secrets.txt
│   ├── courage.txt
│   └── discourses.txt
├── public/
│   └── osho_portrait.jpg
└── .env.local
```

---

## Local LivePortrait Server

Run this on your machine before starting Ngrok:

```bash
# Clone LivePortrait
git clone https://github.com/KwaiVGI/LivePortrait
cd LivePortrait
pip install -r requirements.txt

# Start inference server (custom Flask wrapper needed)
python server.py --port 7860

# In separate terminal — start Ngrok
ngrok http 7860
# Copy the https URL to NGROK_URL in .env.local
```

LivePortrait server.py wrapper to build:
```python
from flask import Flask, request, jsonify
from liveportrait import LivePortraitPipeline
import torch

app = Flask(__name__)
pipeline = LivePortraitPipeline()

@app.route('/animate', methods=['POST'])
def animate():
    data = request.json
    audio_url = data['audio_url']
    source_image = data['source_image']
    
    video_path = pipeline.run(
        source=source_image,
        audio=audio_url
    )
    
    return jsonify({'video_url': video_path})

app.run(port=7860)
```
