import os
from dotenv import load_dotenv

# 1. Load the .env file
load_dotenv()

# 2. Fetch the token
token = os.getenv("HF_TOKEN")

# 3. Print the result safely
if token:
    # Prints just the first 8 characters so you don't leak it in logs
    print(f"✅ Success! Found HF_TOKEN starting with: {token[:8]}...")
else:
    print("❌ Error: HF_TOKEN not found. Check your file name and path.")
