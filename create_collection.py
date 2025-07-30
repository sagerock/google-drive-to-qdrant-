#!/usr/bin/env python3
"""
Helper script to create a new Qdrant collection with the correct configuration
"""

import sys
from qdrant_client import QdrantClient, models
from config import MultiCollectionConfig

def create_collection(collection_name=None):
    """Create a Qdrant collection from multi-collection config"""
    
    # Load multi-collection configuration
    multi_config = MultiCollectionConfig()
    multi_config.validate()
    
    if collection_name:
        # Find specific collection config
        collection_config = None
        for config in multi_config.collections:
            if config.qdrant_collection == collection_name:
                collection_config = config
                break
        
        if not collection_config:
            print(f"✗ Collection '{collection_name}' not found in configuration")
            available = [config.qdrant_collection for config in multi_config.collections]
            print(f"Available collections: {available}")
            return False
    else:
        # Show available collections and let user choose
        print("Available collections to create:")
        for i, config in enumerate(multi_config.collections, 1):
            print(f"  {i}. {config.qdrant_collection} ({config.name})")
        
        choice = input("\nEnter collection number or name: ").strip()
        
        # Try to parse as number first
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(multi_config.collections):
                collection_config = multi_config.collections[idx]
            else:
                print("✗ Invalid choice")
                return False
        except ValueError:
            # Try to find by collection name
            collection_config = None
            for config in multi_config.collections:
                if config.qdrant_collection == choice or config.name == choice:
                    collection_config = config
                    break
            
            if not collection_config:
                print(f"✗ Collection '{choice}' not found")
                return False
    
    # Initialize Qdrant client using collection-specific config
    qdrant_url = collection_config.qdrant_host
    if qdrant_url.startswith('http://') or qdrant_url.startswith('https://'):
        client = QdrantClient(url=qdrant_url, api_key=collection_config.qdrant_api_key)
    else:
        client = QdrantClient(host=qdrant_url, api_key=collection_config.qdrant_api_key)
    
    target_collection = collection_config.qdrant_collection
    
    try:
        # Check if collection already exists
        collections = client.get_collections()
        existing_names = [col.name for col in collections.collections]
        
        if target_collection in existing_names:
            print(f"✓ Collection '{target_collection}' already exists")
            return True
        
        # Create the collection with the same config as your existing one
        client.create_collection(
            collection_name=target_collection,
            vectors_config=models.VectorParams(
                size=1536,  # OpenAI text-embedding dimensions
                distance=models.Distance.COSINE
            ),
            # Enable on-disk payload storage
            on_disk_payload=True
        )
        
        print(f"✓ Successfully created collection '{target_collection}'")
        print(f"  - Collection: {collection_config.name}")
        print(f"  - Vector size: 1536")
        print(f"  - Distance: Cosine")
        print(f"  - On-disk payload: Enabled")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to create collection: {str(e)}")
        return False

if __name__ == "__main__":
    print("Creating Qdrant collection...")
    
    # Check for command line argument
    collection_name = None
    if len(sys.argv) > 1:
        collection_name = sys.argv[1]
        print(f"Target collection: {collection_name}")
    
    # Load and validate config first
    try:
        multi_config = MultiCollectionConfig()
        multi_config.validate()
        print("✓ Configuration validated")
    except Exception as e:
        print(f"✗ Configuration error: {str(e)}")
        exit(1)
    
    success = create_collection(collection_name)
    
    if success:
        print("\n🎉 Collection created successfully!")
        print("You can now run: python3 main.py")
    else:
        print("\n❌ Collection creation failed")
        exit(1)