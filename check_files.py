# check_files.py - Run this to verify your file structure
import os

def check_file_structure():
    """Check if all required files exist and are readable."""
    
    required_files = [
        "static/index.html",
        "static/css/styles.css", 
        "static/js/script.js",
        "api_server.py",
        "discord_bot.py",
        "main.py",
        "config.py",
        "api_key_manager.py",
        "activity_logger.py",
        "rate_limiter.py",
        ".env"
    ]
    
    required_dirs = [
        "static",
        "static/css",
        "static/js",
        "logs"
    ]
    
    print("🔍 Checking Discord Bot file structure...\n")
    
    # Check directories
    print("📁 Directories:")
    for directory in required_dirs:
        if os.path.exists(directory) and os.path.isdir(directory):
            print(f"✅ {directory}")
        else:
            print(f"❌ {directory} - Missing!")
            if directory == "logs":
                os.makedirs(directory, exist_ok=True)
                print(f"✅ Created {directory}")
    
    print("\n📄 Files:")
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ {file_path} - Missing!")
            missing_files.append(file_path)
    
    # Check file permissions
    print("\n🔐 File Permissions:")
    for file_path in required_files:
        if os.path.exists(file_path):
            if os.access(file_path, os.R_OK):
                print(f"✅ {file_path} - Readable")
            else:
                print(f"❌ {file_path} - Not readable!")
        else:
            print(f"⏭️  {file_path} - Skipped (missing)")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"Total required files: {len(required_files)}")
    print(f"Missing files: {len(missing_files)}")
    
    if missing_files:
        print(f"\n❌ Missing files that need to be created:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    else:
        print("\n✅ All required files are present!")
        return True

if __name__ == "__main__":
    check_file_structure()