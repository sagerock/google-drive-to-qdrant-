#!/usr/bin/env python3
"""
Setup script for AWSNA Qdrant AutoUploader
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Create necessary directories."""
    directories = ['credentials']
    
    for directory in directories:
        path = Path(directory)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created directory: {directory}")
        else:
            print(f"✓ Directory already exists: {directory}")

def create_env_file():
    """Create .env file from .env.example if it doesn't exist."""
    env_file = Path('.env')
    example_file = Path('.env.example')
    
    if not env_file.exists() and example_file.exists():
        with open(example_file, 'r') as src, open(env_file, 'w') as dst:
            dst.write(src.read())
        print("✓ Created .env file from .env.example")
        print("  → Please edit .env with your actual configuration values")
    elif env_file.exists():
        print("✓ .env file already exists")
    else:
        print("✗ .env.example not found")

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    else:
        print(f"✓ Python version: {sys.version.split()[0]}")

def install_requirements():
    """Install Python requirements."""
    requirements_file = Path('requirements.txt')
    
    if requirements_file.exists():
        print("Installing Python requirements...")
        os.system(f"pip3 install -r requirements.txt")
        print("✓ Requirements installed")
    else:
        print("✗ requirements.txt not found")

def setup_instructions():
    """Print setup instructions."""
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Set up Google Drive API credentials:")
    print("   - Create service account in Google Cloud Console")
    print("   - Download JSON key file")
    print("   - Save as credentials/service-account.json")
    print("   - Share your Google Drive folder with the service account email")
    print()
    print("2. Configure environment variables:")
    print("   - Edit .env file with your actual values")
    print("   - Get your Google Drive folder ID from the URL")
    print("   - Set up your Qdrant and OpenAI credentials")
    print()
    print("3. Test the setup:")
    print("   python3 main.py")
    print()
    print("4. For GitHub Actions automation:")
    print("   - Set up GitHub repository secrets")
    print("   - Push code to GitHub")
    print("   - Workflow will run every Sunday at 2 AM UTC")
    print("\n" + "="*60)

def main():
    """Main setup function."""
    print("AWSNA Qdrant AutoUploader Setup")
    print("="*40)
    
    check_python_version()
    create_directories()
    create_env_file()
    
    install_deps = input("\nInstall Python requirements? (y/n): ").lower().strip()
    if install_deps in ['y', 'yes']:
        install_requirements()
    
    setup_instructions()

if __name__ == "__main__":
    main()