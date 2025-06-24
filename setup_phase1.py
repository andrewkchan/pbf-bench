#!/usr/bin/env python3
"""
Setup script for Phase 1 of the PBF Comics Benchmark.
Installs dependencies and validates configuration.
"""
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is supported"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version.split()[0]} detected")
    return True

def install_requirements():
    """Install required packages"""
    print("📦 Installing requirements...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Requirements installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install requirements")
        return False

def check_env_file():
    """Check if .env file exists"""
    if not os.path.exists('.env'):
        print("⚠️  .env file not found")
        print("📝 Please copy .env.example to .env and fill in your API keys:")
        print("   cp .env.example .env")
        return False
    print("✅ .env file found")
    return True

def validate_api_keys():
    """Validate that required API keys are present"""
    from dotenv import load_dotenv
    load_dotenv()
    
    required_keys = ['ANTHROPIC_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']
    missing_keys = []
    
    for key in required_keys:
        if not os.getenv(key):
            missing_keys.append(key)
    
    if missing_keys:
        print(f"❌ Missing API keys: {', '.join(missing_keys)}")
        print("Please add them to your .env file")
        return False
    
    print("✅ All required API keys found")
    return True

def check_comics_data():
    """Check if comics data is available"""
    if not os.path.exists('pbf_comics_metadata.json'):
        print("⚠️  Comics metadata not found")
        print("📥 Please run the comic download script first:")
        print("   python3 download_pbf_comics_regex.py")
        return False
    
    if not os.path.exists('pbf_comics') or not os.listdir('pbf_comics'):
        print("⚠️  Comics images not found")
        print("📥 Please run the comic download script first:")
        print("   python3 download_pbf_comics_regex.py")
        return False
    
    print("✅ Comics data found")
    return True

def main():
    print("🚀 Setting up Phase 1: Ground Truth Labeling")
    print("=" * 50)
    
    success = True
    
    # Check Python version
    success &= check_python_version()
    
    # Install requirements
    success &= install_requirements()
    
    # Check .env file
    success &= check_env_file()
    
    if os.path.exists('.env'):
        # Validate API keys
        success &= validate_api_keys()
    
    # Check comics data
    success &= check_comics_data()
    
    print("\n" + "=" * 50)
    
    if success:
        print("🎉 Setup complete! You can now:")
        print("1. Generate AI explanations: python3 generate_explanations.py")
        print("2. Start labeling web app: python3 labeling_app.py")
    else:
        print("❌ Setup incomplete. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())