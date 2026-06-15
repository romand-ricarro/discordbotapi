# check_static_files.py
import os

def check_static_files_structure():
    """Check if the static files structure is correct."""
    
    # Check if the static directory exists
    if not os.path.exists("static"):
        print("❌ static directory not found. Creating it...")
        os.makedirs("static")
        os.makedirs("static/css")
        os.makedirs("static/js")
        print("✅ Created static directory structure")
        return False
    
    # Check if the css directory exists
    if not os.path.exists("static/css"):
        print("❌ static/css directory not found. Creating it...")
        os.makedirs("static/css")
        print("✅ Created static/css directory")
    
    # Check if the js directory exists
    if not os.path.exists("static/js"):
        print("❌ static/js directory not found. Creating it...")
        os.makedirs("static/js")
        print("✅ Created static/js directory")
    
    # Check if the index.html file exists
    if not os.path.exists("static/index.html"):
        print("❌ static/index.html file not found!")
        return False
    
    # Check if the styles.css file exists
    if not os.path.exists("static/css/styles.css"):
        print("❌ static/css/styles.css file not found!")
        return False
    
    # Check if the script.js file exists
    if not os.path.exists("static/js/script.js"):
        print("❌ static/js/script.js file not found!")
        return False
    
    # Check file sizes
    index_size = os.path.getsize("static/index.html")
    css_size = os.path.getsize("static/css/styles.css")
    js_size = os.path.getsize("static/js/script.js")
    
    print(f"📄 static/index.html: {index_size} bytes")
    print(f"📄 static/css/styles.css: {css_size} bytes")
    print(f"📄 static/js/script.js: {js_size} bytes")
    
    # Check for any permission issues
    try:
        with open("static/index.html", "r") as f:
            index_head = f.read(100)
        with open("static/css/styles.css", "r") as f:
            css_head = f.read(100)
        with open("static/js/script.js", "r") as f:
            js_head = f.read(100)
        
        print("✅ All files are readable")
    except Exception as e:
        print(f"❌ Permission error: {e}")
        return False
    
    print("✅ Static files structure looks good!")
    return True

if __name__ == "__main__":
    check_static_files_structure()