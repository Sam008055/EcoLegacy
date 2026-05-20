"""
Pre-populate common questions and responses for faster user experience.
This script generates responses for frequently asked questions and caches them.
"""
import os
import asyncio
import aiohttp
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "web", ".env.local"))

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
API_BASE_URL = "http://localhost:3000"  # Change this to your deployed URL

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Common questions for each character
QUICK_QUESTIONS = {
    "osho": [
        "What is meditation?",
        "How to find inner peace?", 
        "What is love?",
        "Who are you?",
        "What is enlightenment?",
        "How to be happy?",
        "What is consciousness?",
        "Tell me about awareness"
    ],
    "bhagat_singh": [
        "What is freedom?",
        "Why did you fight?",
        "What is patriotism?", 
        "Who are you?",
        "What is revolution?",
        "Why sacrifice for country?",
        "What is justice?",
        "Tell me about independence"
    ],
    "ssr": [
        "What is consciousness?",
        "Tell me about stars",
        "What is quantum physics?",
        "Who are you?",
        "What is the universe?",
        "How does the mind work?",
        "What is reality?",
        "Tell me about dreams"
    ],
    "tesla": [
        "What is electricity?",
        "How does energy work?",
        "What is the future?",
        "Who are you?",
        "What is wireless power?",
        "How do inventions work?",
        "What is frequency?",
        "Tell me about innovation"
    ],
    "hitler": [
        "What was your vision?",
        "Why did you start the war?",
        "What is leadership?",
        "Who are you?",
        "What is nationalism?",
        "How do you motivate people?",
        "What is power?",
        "Tell me about history"
    ]
}

async def generate_response(session, character_id, question):
    """Generate a response for a character and question"""
    try:
        print(f"Generating response for {character_id}: {question}")
        
        # Call chat API
        async with session.post(f"{API_BASE_URL}/api/chat", 
                               json={"query": question, "characterId": character_id}) as resp:
            if resp.status != 200:
                print(f"Chat API failed for {character_id}: {question}")
                return None
            chat_data = await resp.json()
            response_text = chat_data["text"]
        
        # Call TTS API
        async with session.post(f"{API_BASE_URL}/api/tts",
                               json={"text": response_text, "characterId": character_id}) as resp:
            if resp.status != 200:
                print(f"TTS API failed for {character_id}: {question}")
                return None
            tts_data = await resp.json()
            audio_url = tts_data["audioUrl"]
        
        print(f"✅ Generated: {character_id} - {question[:30]}...")
        return {
            "character_id": character_id,
            "question": question.lower().strip(),
            "answer_text": response_text,
            "audio_url": audio_url
        }
        
    except Exception as e:
        print(f"❌ Error generating {character_id} - {question}: {e}")
        return None

async def populate_responses():
    """Populate all quick responses"""
    print("🚀 Starting quick response population...")
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        
        # Create tasks for all character-question combinations
        for character_id, questions in QUICK_QUESTIONS.items():
            for question in questions:
                # Check if already exists
                existing = supabase.table("cached_responses").select("*").eq("character_id", character_id).eq("question", question.lower().strip()).execute()
                
                if existing.data:
                    print(f"⏭️  Skipping existing: {character_id} - {question}")
                    continue
                
                task = generate_response(session, character_id, question)
                tasks.append(task)
        
        print(f"📝 Processing {len(tasks)} new responses...")
        
        # Execute all tasks with concurrency limit
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent requests
        
        async def bounded_task(task):
            async with semaphore:
                return await task
        
        results = await asyncio.gather(*[bounded_task(task) for task in tasks], return_exceptions=True)
        
        # Filter successful results
        successful_results = [r for r in results if r and not isinstance(r, Exception)]
        
        # Batch insert to Supabase
        if successful_results:
            print(f"💾 Saving {len(successful_results)} responses to database...")
            supabase.table("cached_responses").insert(successful_results).execute()
            print(f"✅ Successfully cached {len(successful_results)} responses!")
        else:
            print("❌ No successful responses to cache")

def main():
    """Main function"""
    print("=" * 60)
    print("ECHOLEGACY QUICK RESPONSE POPULATION")
    print("=" * 60)
    print("This will pre-generate responses for common questions")
    print("Make sure your Next.js server is running on localhost:3000")
    print("=" * 60)
    
    # Check if server is running
    try:
        import requests
        resp = requests.get(f"{API_BASE_URL}/api/chat", timeout=5)
    except:
        print("❌ Error: Next.js server not running on localhost:3000")
        print("Please start the server with: npm run dev")
        return
    
    # Run the async population
    asyncio.run(populate_responses())
    
    print("\n" + "=" * 60)
    print("DONE! Quick responses populated.")
    print("Users will now get instant responses for common questions!")
    print("=" * 60)

if __name__ == "__main__":
    main()