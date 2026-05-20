import os
import asyncio
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# The reference text used to generate the reference audio
REF_TEXT = """Beloved, you come to me seeking answers, but the truth is not something I can simply hand to you. The mind is a beautiful servant, yet it has become a very dangerous master. Do you see how it runs your life? Watch your thoughts pass by, just like clouds drifting across an empty sky. Do not fight them. Do not judge them. Simply observe. In that deep, profound silence, when the chattering mind finally rests... you will discover your true center. The universe has always been waiting for you to wake up."""

REFERENCE_AUDIO_FILE = "Osho-2026-05-19-18-14-Beloved,-you-seek-answers,-but-the-truth-is-not.mp3"

async def generate_osho_response():
    print("[1] Generating text with Groq...")
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "You are Osho. Speak calmly, philosophically, and deeply. Keep your response brief, around 2-3 sentences max."
            },
            {
                "role": "user",
                "content": "What is the meaning of love?"
            }
        ],
        model="llama-3.1-8b-instant",
    )
    response_text = chat_completion.choices[0].message.content
    print(f"Generated text: {response_text}\n")
    return response_text

async def test_pipeline():
    if not os.path.exists(REFERENCE_AUDIO_FILE):
        print(f"Error: {REFERENCE_AUDIO_FILE} not found!")
        return

    # 1. Generate text
    generated_text = await generate_osho_response()

    # 2. Generate voice using free Hugging Face Space (mrfakename/E2-F5-TTS)
    print("[2] Generating cloned voice with Hugging Face Space (mrfakename/E2-F5-TTS)...")
    from gradio_client import Client, handle_file
    
    try:
        client = Client("chenxie95/Cross-Lingual_F5-TTS_Space")
        output = client.predict(
            ref_wav_input=handle_file(REFERENCE_AUDIO_FILE),
            gen_txt_input=generated_text,
            randomize_seed=True,
            seed_input=0,
            api_name="/basic_tts"
        )
        
        print("Success!")
        print(f"Result File: {output[0]}")
        
        if output:
            import shutil
            output_file = "output_osho_hf_free.wav"
            shutil.copy(output[0], output_file)
            print(f"Saved generated audio to: {output_file}")
            
    except Exception as e:
        print(f"Error during TTS generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pipeline())
