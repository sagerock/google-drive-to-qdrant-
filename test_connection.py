#!/usr/bin/env python3
"""
Quick test script to verify Google Drive connection
"""

try:
    from google_drive_handler import GoogleDriveHandler
    print("✓ Importing GoogleDriveHandler successful")
    
    handler = GoogleDriveHandler()
    print("✓ Google Drive connection successful!")
    
except Exception as e:
    print(f"✗ Connection failed: {str(e)}")
    print("\nMake sure you have:")
    print("1. Created credentials/service-account.json")
    print("2. Set up your .env file")
    print("3. Installed requirements: pip3 install -r requirements.txt")