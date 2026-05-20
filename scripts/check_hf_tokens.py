"""
Check HuggingFace token status and quotas.
This helps you see which tokens are working and which hit quota limits.
"""
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "web", ".env.local"))

# Get all HF tokens
HF_TOKENS = [
    os.environ.get("HUGGINGFACE_TOKEN"),
    os.environ.get("HUGGINGFACE_TOKEN_1"),
    os.environ.get("HUGGINGFACE_TOKEN_2"),
    os.environ.get("HUGGINGFACE_TOKEN_3"),
    os.environ.get("HUGGINGFACE_TOKEN_4"),
    os.environ.get("HUGGINGFACE_TOKEN_5"),
    os.environ.get("HUGGINGFACE_TOKEN_6"),
    os.environ.get("HUGGINGFACE_TOKEN_7"),
    os.environ.get("HUGGINGFACE_TOKEN_8"),
    os.environ.get("HUGGINGFACE_TOKEN_9"),
]

# Filter out None values
HF_TOKENS = [token for token in HF_TOKENS if token]

async def check_token_status(session, token, index):
    """Check if a HuggingFace token is working"""
    try:
        # Try to access the HF API with this token
        headers = {"Authorization": f"Bearer {token}"}
        
        async with session.get("https://huggingface.co/api/whoami", headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                username = data.get("name", "Unknown")
                print(f"✅ Token {index + 1}: WORKING (User: {username})")
                return True
            else:
                print(f"❌ Token {index + 1}: FAILED (Status: {resp.status})")
                return False
                
    except Exception as e:
        print(f"❌ Token {index + 1}: ERROR ({str(e)})")
        return False

async def main():
    """Check all tokens"""
    print("🔍 Checking HuggingFace Token Status...")
    print("=" * 50)
    
    if not HF_TOKENS:
        print("❌ No HuggingFace tokens found in environment variables!")
        print("Add tokens to your .env.local file:")
        print("HUGGINGFACE_TOKEN=hf_xxx")
        print("HUGGINGFACE_TOKEN_1=hf_yyy")
        return
    
    print(f"Found {len(HF_TOKENS)} tokens to check...")
    print()
    
    async with aiohttp.ClientSession() as session:
        tasks = [check_token_status(session, token, i) for i, token in enumerate(HF_TOKENS)]
        results = await asyncio.gather(*tasks)
    
    working_count = sum(results)
    print()
    print("=" * 50)
    print(f"📊 SUMMARY: {working_count}/{len(HF_TOKENS)} tokens are working")
    
    if working_count == 0:
        print("🚨 ALL TOKENS FAILED!")
        print("This usually means:")
        print("1. Tokens hit their 60s ZeroGPU quota")
        print("2. Invalid tokens")
        print("3. Network issues")
        print()
        print("💡 SOLUTIONS:")
        print("1. Wait for quota reset (usually 24 hours)")
        print("2. Create new HuggingFace accounts")
        print("3. Get HuggingFace Pro subscription")
    elif working_count < len(HF_TOKENS):
        print(f"⚠️  {len(HF_TOKENS) - working_count} tokens need attention")
    else:
        print("🎉 All tokens are working!")

if __name__ == "__main__":
    asyncio.run(main())