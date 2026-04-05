import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. Setup - Replace with your actual token if not in environment
tok = os.getenv("HF_TOKEN") or "your_hf_token_here"
base = "https://router.huggingface.co/v1"
mod = "Qwen/Qwen2.5-72B-Instruct"

client = OpenAI(base_url=base, api_key=tok)

print(f"Testing connection to {mod}...")

try:
    res = client.chat.completions.create(
        model=mod,
        messages=[{"role": "user", "content": "Say 'Connection Success and your name and todays date'"}],
        max_tokens=10
    )
    print("RESULT:", res.choices[0].message.content)
except Exception as e:
    print("\n[!] CONNECTION FAILED")
    print(f"Error Type: {type(e).__name__}")
    print(f"Details: {e}")
    
    if "404" in str(e):
        print("FIX: The model ID might be wrong or not on the serverless router.")
    elif "401" in str(e):
        print("FIX: Check your HF_TOKEN. Ensure it has 'Read' or 'Inference' access.")