# EchoLegacy — Build Checklist & Day-by-Day Plan

---

## Pre-Build Setup (Do Today)

- [ ] Create Next.js project: `npx create-next-app@latest echolegacy`
- [ ] Install dependencies:
  ```bash
  npm install @google/generative-ai @supabase/supabase-js firebase
  npm install @google-cloud/speech  # backup STT if Web Speech fails
  ```
- [ ] Create accounts/projects:
  - [ ] Supabase project — enable pgvector extension
  - [ ] Firebase project — Realtime DB + Storage
  - [ ] Get Gemini API key from Google AI Studio (free)
  - [ ] Note Fish.audio API key + Osho voice ID
- [ ] Download Osho corpus:
  - [ ] The Book of Secrets (PDF → convert to TXT)
  - [ ] Courage / Awareness / any Osho book excerpts (TXT)
  - [ ] Discourse transcripts (TXT — available widely online)
- [ ] Clone LivePortrait locally
- [ ] Install Ngrok

---

## Day 1 — Core Pipeline Working

Goal: One working voice conversation with Osho

- [ ] Set up Supabase schema (run SQL from system design doc)
- [ ] Run corpus ingestion script
- [ ] Build `/api/chat` route (RAG + Gemini)
- [ ] Build `/api/speak` route (Fish.audio)
- [ ] Test: type a question → get Osho's voice response
- [ ] Basic UI: dark background, Osho photo, text input, audio plays

**Day 1 done when:** You can type "What is meditation?" and hear Osho's voice respond accurately.

---

## Day 2 — Voice Input + LivePortrait

Goal: Full voice-to-voice with animated portrait

- [ ] Add Web Speech API voice input
- [ ] Set up LivePortrait local server
- [ ] Start Ngrok tunnel
- [ ] Build `/api/animate` route
- [ ] Wire: speak → get audio → send to LivePortrait → display video
- [ ] Add fallback: if LivePortrait fails, show static photo + audio
- [ ] Test full flow: speak question → see Osho's face move → hear response

---

## Day 3 — Polish + Deploy

Goal: Shareable link working

- [ ] Firebase conversation logging
- [ ] Audio response caching (Firebase Storage)
- [ ] Pre-generate 20 seed responses (cache them)
- [ ] Session limit: max 7 exchanges per user
- [ ] UI polish: animations, loading states, "Osho is reflecting..." indicator
- [ ] Deploy to Vercel
- [ ] Test on mobile browser
- [ ] Share link with 5 friends — get first real users

---

## Day 4-5 — Buffer / AR Exploration

- [ ] Fix bugs from real user feedback
- [ ] If time: explore React Native AR setup
- [ ] Optimize LivePortrait latency
- [ ] Add conversation sharing feature (screenshot button)

---

## Day 6-7 — Hackathon Prep

- [ ] Prepare demo script (under 2 minutes)
- [ ] Pre-generate best demo responses as cached MP4
- [ ] Create demo video/reel for social posting
- [ ] Prepare pitch: problem → solution → demo → market → revenue
- [ ] Test on different devices and networks

---

## Hackathon Day (June 22) — 48 Hours

### Hour 0-2: Launch
- [ ] Post demo video: "I built something. You can talk to Osho. In his voice. Live."
- [ ] Share link in college WhatsApp groups
- [ ] Twitter/Instagram post

### Hour 3-12: Build + Engage
- [ ] Keep building/fixing based on user feedback
- [ ] Respond to every comment and DM personally
- [ ] Screenshot interesting conversations users share

### Hour 12-24: Content Push
- [ ] Post: "Someone asked Osho about anxiety. Here's what he said." [screenshot]
- [ ] Post: "50 people have talked to Osho in 12 hours"
- [ ] Reddit: r/india, r/meditation, r/osho

### Hour 24-36: Double Down
- [ ] Post the wildest/most emotional conversation
- [ ] Tag educators, spiritual influencers
- [ ] Collect testimonials

### Hour 36-48: Final Push
- [ ] Compile user count, conversations, reactions
- [ ] Prepare judge demo
- [ ] One final big post before judging

---

## Demo Script for Judges (2 minutes)

```
"India has 250 million students with no access to quality mentorship.
Osho's wisdom exists — in hundreds of books, thousands of hours of discourse.
But it's static. You can't ask The Book of Secrets about YOUR anxiety.

EchoLegacy changes that.

[Demo: speak a question live]
[Judge hears Osho's voice respond]

This isn't a chatbot with Osho's name on it.
Every response is grounded in his actual discourses through RAG.
He won't say anything he never said.

[Show conversation history]
[Show user count]

In 48 hours, X real users have spoken to Osho.
We're starting with Osho. Rumi, Kalam, Vivekananda, Einstein are next.
This is infrastructure for human wisdom — not one product, a platform.

Revenue: freemium ₹99/month, B2B school licenses, figure marketplace.
TAM: 250M Indian students + global spiritual seekers."
```

---

## Key Commands Reference

```bash
# Start dev server
npm run dev

# Run corpus ingestion (once)
node scripts/ingest.js

# Start LivePortrait server (on your machine)
cd LivePortrait && python server.py

# Start Ngrok (new terminal)
ngrok http 7860

# Deploy to Vercel
vercel --prod
```

---

## Emergency Fallbacks

| If this breaks | Do this |
|----------------|---------|
| LivePortrait crashes | Static Osho photo + audio plays. Still impressive. |
| Ngrok drops | Switch to audio-only mode automatically |
| Fish.audio credits low | Serve cached responses only |
| Gemini rate limit | Add 2s delay between requests, show "thinking" animation |
| Supabase down | Fallback to hardcoded top 10 Osho passages in memory |
| Vercel cold start slow | Pre-warm by hitting /api/chat on deploy |
