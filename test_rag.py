import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from groq import Groq

# Load environment variables
load_dotenv(".env.local")
load_dotenv(".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
REFERENCE_AUDIO_FILE = "Osho-2026-05-19-18-14-Beloved,-you-seek-answers,-but-the-truth-is-not.mp3"

async def test_rag_and_tts(query="What is the meaning of life?"):
    print(f"--- Testing Pipeline ---")
    print(f"Query: {query}\n")

    # 1. Generate Embedding
    print("[1] Loading embedding model (all-mpnet-base-v2) and embedding query...")
    try:
        model = SentenceTransformer("all-mpnet-base-v2")
        query_embedding = model.encode(query, normalize_embeddings=True).tolist()
    except Exception as e:
        print(f"[ERROR] Error generating embedding: {e}")
        return

    # 2. Query Supabase (RAG)
    print("\n[2] Searching Supabase for relevant context...")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        response = supabase.rpc('match_documents', {
            'query_embedding': query_embedding,
            'match_threshold': 0.1, # Lowered threshold to ensure we get results
            'match_count': 3
        }).execute()

        context_chunks = response.data
        if not context_chunks:
            print("[WARN] No relevant context found in Supabase.")
            context_text = "No context available."
        else:
            print(f"[OK] Found {len(context_chunks)} relevant chunks.")
            context_text = "\n\n".join([chunk['content'] for chunk in context_chunks])
            # Print a snippet of the context
            print(f"Snippet of context: {context_text[:200]}...")
    except Exception as e:
        print(f"[ERROR] Error querying Supabase: {e}")
        return

    # 3. Generate Text with Groq
    print("\n[3] Generating response with Groq using RAG context...")
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        system_prompt = f"""You are Osho. Speak calmly, philosophically, and deeply. 
Keep your response brief, around 2-3 sentences max. 
Base your response strictly on the following context from your discourses.

Context:
{context_text}
"""

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model="llama-3.1-8b-instant",
        )
        response_text = chat_completion.choices[0].message.content
        print(f"[OK] Generated text: {response_text}")
    except Exception as e:
        print(f"[ERROR] Error generating text with Groq: {e}")
        return

    # 4. Generate TTS with F5-TTS (Hugging Face Space)
    print("\n[4] Generating cloned voice with F5-TTS...")
    if not os.path.exists(REFERENCE_AUDIO_FILE):
        print(f"[ERROR] Error: Reference audio file {REFERENCE_AUDIO_FILE} not found!")
        return

    from gradio_client import Client as GradioClient, handle_file
    try:
        gradio_client = GradioClient("chenxie95/Cross-Lingual_F5-TTS_Space")
        output = gradio_client.predict(
            ref_wav_input=handle_file(REFERENCE_AUDIO_FILE),
            gen_txt_input=response_text,
            randomize_seed=True,
            seed_input=0,
            api_name="/basic_tts"
        )
        
        if output:
            import shutil
            output_file = "output_rag_osho.wav"
            shutil.copy(output[0], output_file)
            print(f"[OK] Success! Saved generated audio to: {output_file}")
        else:
            print("[ERROR] No output from F5-TTS.")
            
    except Exception as e:
        print(f"[ERROR] Error during TTS generation: {e}")

if __name__ == "__main__":
    asyncio.run(test_rag_and_tts())
