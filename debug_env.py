import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the environment variables
token = os.getenv("DISCORD_BOT_TOKEN")
api_key = os.getenv("API_KEY")
api_port = os.getenv("API_PORT")

# Print debug info (but hide most of the token for security)
if token:
    token_preview = token[:5] + "..." + token[-5:] if len(token) > 10 else "***"
    print(f"✅ DISCORD_BOT_TOKEN is set: {token_preview}")
else:
    print("❌ DISCORD_BOT_TOKEN is NOT set")

if api_key:
    api_key_preview = api_key[:5] + "..." + api_key[-5:] if len(api_key) > 10 else "***"
    print(f"✅ API_KEY is set: {api_key_preview}")
    # Check if it matches what you're using in curl
    test_key = os.getenv("EXPECTED_API_KEY", "")  # Set EXPECTED_API_KEY in .env for comparison
    if api_key == test_key:
        print("✅ API_KEY matches the one you're using in curl!")
    else:
        print("❌ API_KEY does NOT match the one you're using in curl:")
        print(f"  - Expected: {test_key}")
        print(f"  - Found: {api_key}")
else:
    print("❌ API_KEY is NOT set")

if api_port:
    print(f"✅ API_PORT is set: {api_port}")
else:
    print("✅ API_PORT is not set, will use default: 8000")

# Print current directory and .env file path
print(f"\nCurrent directory: {os.getcwd()}")
env_path = os.path.join(os.getcwd(), '.env')
if os.path.exists(env_path):
    print(f"✅ .env file exists at: {env_path}")
    
    # Print file stats to check permissions
    import stat
    st = os.stat(env_path)
    print(f"  - File permissions: {stat.filemode(st.st_mode)}")
    print(f"  - File size: {st.st_size} bytes")
else:
    print(f"❌ .env file NOT found at: {env_path}")