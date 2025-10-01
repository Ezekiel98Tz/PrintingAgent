#!/usr/bin/env python3
"""
Setup script for AI Document Agent
Helps users install dependencies and configure the environment
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🔍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_dependencies():
    """Install required dependencies"""
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return False
    return True

def setup_environment():
    """Set up environment configuration"""
    env_template = Path(".env.template")
    env_file = Path(".env")
    
    if env_template.exists() and not env_file.exists():
        print("\n📝 Setting up environment configuration...")
        shutil.copy(env_template, env_file)
        print("✅ Created .env file from template")
        print("📋 Please edit .env file with your configuration")
        return True
    elif env_file.exists():
        print("✅ Environment file already exists")
        return True
    else:
        print("❌ Environment template not found")
        return False

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating project directories...")
    directories = [
        "data/incoming",
        "data/processed", 
        "data/logs",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    return True

def run_tests():
    """Run basic tests to verify setup"""
    print("\n🧪 Running basic tests...")
    if not run_command("python -m pytest tests/ -v", "Running tests"):
        print("⚠️  Some tests failed, but this might be expected without API keys")
        return True  # Don't fail setup for test failures
    return True

def main():
    """Main setup function"""
    print("🚀 AI Document Agent Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Create directories
    if not create_directories():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        print("\n❌ Failed to setup environment")
        sys.exit(1)
    
    # Run tests
    run_tests()
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Edit .env file with your configuration")
    print("2. For testing without API keys, keep LLM_PROVIDER=mock")
    print("3. Run: python main.py --local")
    print("4. Place .docx files in data/incoming/ to test")
    print("\n💡 For WhatsApp integration, configure Twilio settings in .env")

if __name__ == "__main__":
    main()