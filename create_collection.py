#!/usr/bin/env python3
"""
Helper script to create a new Qdrant collection with the correct configuration
"""

from qdrant_client import QdrantClient, models
from config import Config

def create_collection():
    """Create the awsna_accreditation_auto collection"""
    
    # Initialize Qdrant client
    qdrant_url = Config.QDRANT_HOST
    if qdrant_url.startswith('http://') or qdrant_url.startswith('https://'):
        client = QdrantClient(url=qdrant_url, api_key=Config.QDRANT_API_KEY)
    else:
        client = QdrantClient(host=qdrant_url, api_key=Config.QDRANT_API_KEY)
    
    collection_name = "awsna_accreditation_auto"
    
    try:
        # Check if collection already exists
        collections = client.get_collections()
        existing_names = [col.name for col in collections.collections]
        
        if collection_name in existing_names:
            print(f"✓ Collection '{collection_name}' already exists")
            return True
        
        # Create the collection with the same config as your existing one
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1536,  # OpenAI text-embedding-ada-002 dimensions
                distance=models.Distance.COSINE
            ),
            # Enable on-disk payload storage
            on_disk_payload=True
        )
        
        print(f"✓ Successfully created collection '{collection_name}'")
        print(f"  - Vector size: 1536")
        print(f"  - Distance: Cosine")
        print(f"  - On-disk payload: Enabled")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create collection: {str(e)}")
        return False

if __name__ == "__main__":
    print("Creating Qdrant collection...")
    
    # Validate config first
    try:
        Config.validate()
        print("✓ Configuration validated")
    except Exception as e:
        print(f"✗ Configuration error: {str(e)}")
        exit(1)
    
    success = create_collection()
    
    if success:
        print("\n🎉 Collection created successfully!")
        print("You can now run: python3 main.py")
    else:
        print("\n❌ Collection creation failed")
        exit(1)