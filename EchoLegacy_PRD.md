# EchoLegacy — Product Requirements Document
**Version:** 1.1  
**Author:** Samarth Pasalkar  
**Hackathon:** Open Innovation — June 22, 2026  
**Stack:** Next.js · Gemini API · Fish.audio · Supabase · Firebase · LivePortrait · Ngrok

---

## 1. Product Vision

> "Great minds left us their wisdom in books nobody reads. What if you could just ask them?"

EchoLegacy lets you have a real, voice-to-voice conversation with historical figures — powered by their actual writings, speaking in their real voice, in real time. The first figure: **Osho (Rajneesh)**.

The gap: Osho's books, lectures, and discourses exist — thousands of hours of content. But they are static. A person struggling with anxiety cannot ask "The Book of Secrets" for personal advice. EchoLegacy closes that gap — making wisdom conversational, personal, and alive.

---

## 2. Problem Statement

- 250M+ students in India have no access to quality mentorship
- Great thinkers' wisdom is locked in books nobody reads deeply
- Existing AI chatbots hallucinate views of historical figures without grounding
- No product exists that combines authentic voice + accurate persona + real-time conversation

---

## 3. Target Users

| User | Need |
|------|------|
| Spiritual seekers (18–40) | Personal guidance, meditation advice, existential questions |
| Philosophy enthusiasts | Deep intellectual conversation |
| Students & young adults | Life decisions, stress, purpose |
| General public | Emotional connection to a beloved thinker |

---

## 4. Core User Flow

```
1. User opens EchoLegacy web app
2. Sees Osho's portrait on a dark, atmospheric interface
3. Presses mic button → speaks their question
4. Web Speech API captures and transcribes
5. Query hits RAG pipeline → retrieves relevant Osho passages
6. Gemini Flash generates response grounded in Osho's actual words
7. Fish.audio synthesizes response in Osho's voice
8. LivePortrait animates Osho's portrait to match audio
9. User hears and sees Osho respond
10. Conversation continues naturally
11. Session logged to Firebase
```

---

## 5. Features

### MVP (Must have for hackathon)
- [ ] Voice input via Web Speech API
- [ ] RAG over Osho's corpus (Supabase pgvector + Gemini embeddings)
- [ ] Gemini Flash response generation with Osho persona
- [ ] Fish.audio TTS with Osho voice model
- [ ] LivePortrait talking portrait (Ngrok tunnel to local GPU)
- [ ] Conversation history (Firebase)
- [ ] Clean dark atmospheric UI
- [ ] Deployed on Vercel (audio only fallback if Ngrok down)

### V2 (Post hackathon)
- [ ] Multiple historical figures (Kalam, Vivekananda, Einstein, Rumi)
- [ ] Mobile app (React Native)
- [ ] AR mode — figure appears in your room
- [ ] User accounts, saved conversations
- [ ] Freemium paywall

---

## 6. Technical Constraints

| Constraint | Detail |
|------------|--------|
| Zero API cost | Gemini free tier, Fish.audio credits, Ngrok free |
| GPU dependent | LivePortrait runs on local RTX 3050 4GB via Ngrok |
| Hallucination prevention | All responses must be grounded in retrieved RAG passages |
| Latency target | Under 8 seconds end to end for full response |
| Concurrent users | Limited by Ngrok free tier (1 tunnel, ~40 req/min) |

---

## 7. Success Metrics (Hackathon)

- Working end-to-end voice conversation demo
- Minimum 20 real users during hackathon 48hrs
- At least 5 shareable conversation screenshots
- Judge demo under 2 minutes, emotionally clear

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| LivePortrait too slow on 3050 | Fallback: static photo + audio only |
| Ngrok tunnel drops | Pre-cache 20 common responses as MP4 |
| Gemini hallucination | Strict RAG grounding, refuse out-of-corpus questions |
| Fish.audio credits drain | Cap session at 7 exchanges, cache audio files |
| Legal (personality rights) | Hackathon only, non-commercial, educational framing |
