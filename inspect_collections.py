#!/usr/bin/env python3
"""
Collection Inspection Utility
Shows what documents are currently indexed in your Qdrant collections.
"""

import sys
import json
from collections import defaultdict
from datetime import datetime
from qdrant_client import QdrantClient
from config import MultiCollectionConfig

def inspect_collection(collection_config, detailed=False):
    """Inspect a single collection and return document information."""
    
    # Initialize Qdrant client
    qdrant_url = collection_config.qdrant_host
    if qdrant_url.startswith('http://') or qdrant_url.startswith('https://'):
        client = QdrantClient(url=qdrant_url, api_key=collection_config.qdrant_api_key)
    else:
        client = QdrantClient(host=qdrant_url, api_key=collection_config.qdrant_api_key)
    
    collection_name = collection_config.qdrant_collection
    
    try:
        # Get collection info
        collection_info = client.get_collection(collection_name)
        total_points = collection_info.points_count
        
        print(f"\n📁 Collection: {collection_config.name}")
        print(f"   Qdrant Collection: {collection_name}")
        print(f"   Total Chunks: {total_points}")
        
        if total_points == 0:
            print("   ⚠️ No documents indexed")
            return
        
        # Get sample points to analyze documents
        scroll_result = client.scroll(
            collection_name=collection_name,
            limit=min(1000, total_points),  # Get up to 1000 points for analysis
            with_payload=True,
            with_vectors=False
        )
        
        points, _ = scroll_result
        
        # Analyze documents
        documents = defaultdict(lambda: {
            'chunks': 0,
            'size': 0,
            'mimeType': 'unknown',
            'modifiedTime': 'unknown',
            'source': 'unknown'
        })
        
        for point in points:
            payload = point.payload
            metadata = payload.get('metadata', {})
            
            file_name = metadata.get('fileName', 'Unknown File')
            documents[file_name]['chunks'] += 1
            documents[file_name]['size'] = metadata.get('size', 0)
            documents[file_name]['mimeType'] = metadata.get('mimeType', 'unknown')
            documents[file_name]['modifiedTime'] = metadata.get('modifiedTime', 'unknown')
            documents[file_name]['source'] = metadata.get('source', 'unknown')
        
        print(f"   📄 Unique Documents: {len(documents)}")
        print(f"   🧩 Average Chunks per Document: {total_points / len(documents):.1f}")
        
        # Show documents
        if detailed:
            print(f"\n   📋 Document Details:")
            for i, (file_name, info) in enumerate(sorted(documents.items()), 1):
                size_mb = info['size'] / 1024 / 1024 if info['size'] > 0 else 0
                mime_short = info['mimeType'].split('/')[-1] if '/' in info['mimeType'] else info['mimeType']
                
                # Parse modification time
                mod_time = 'unknown'
                if info['modifiedTime'] != 'unknown':
                    try:
                        dt = datetime.fromisoformat(info['modifiedTime'].replace('Z', '+00:00'))
                        mod_time = dt.strftime('%Y-%m-%d')
                    except:
                        mod_time = info['modifiedTime'][:10]
                
                print(f"      {i:2d}. {file_name}")
                print(f"          📊 {info['chunks']} chunks | 📁 {size_mb:.1f}MB | 🏷️ {mime_short} | 📅 {mod_time}")
        else:
            print(f"\n   📄 Document List (first 10):")
            for i, file_name in enumerate(sorted(documents.keys())[:10], 1):
                chunks = documents[file_name]['chunks']
                print(f"      {i:2d}. {file_name} ({chunks} chunks)")
            
            if len(documents) > 10:
                print(f"      ... and {len(documents) - 10} more documents")
        
        return {
            'collection_name': collection_config.name,
            'qdrant_collection': collection_name,
            'total_points': total_points,
            'total_documents': len(documents),
            'documents': dict(documents)
        }
        
    except Exception as e:
        print(f"   ❌ Error inspecting collection: {str(e)}")
        return None

def main():
    """Main inspection function."""
    
    # Parse command line arguments
    detailed = '--detailed' in sys.argv or '-d' in sys.argv
    target_collection = None
    
    for arg in sys.argv[1:]:
        if not arg.startswith('-'):
            target_collection = arg
            break
    
    try:
        # Load configuration
        multi_config = MultiCollectionConfig()
        multi_config.validate()
        
        print("🔍 QDRANT COLLECTION INSPECTION")
        print("=" * 50)
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if target_collection:
            # Find and inspect specific collection
            collection_config = None
            for config in multi_config.collections:
                if (config.name == target_collection or 
                    config.qdrant_collection == target_collection):
                    collection_config = config
                    break
            
            if not collection_config:
                available = [f"{config.name} ({config.qdrant_collection})" for config in multi_config.collections]
                print(f"\n❌ Collection '{target_collection}' not found.")
                print(f"Available collections: {', '.join(available)}")
                sys.exit(1)
            
            result = inspect_collection(collection_config, detailed=True)
            
        else:
            # Inspect all collections
            print(f"📊 Found {len(multi_config.collections)} collection(s) to inspect")
            
            all_results = []
            total_documents = 0
            total_chunks = 0
            
            for collection_config in multi_config.collections:
                result = inspect_collection(collection_config, detailed=detailed)
                if result:
                    all_results.append(result)
                    total_documents += result['total_documents']
                    total_chunks += result['total_points']
            
            # Summary
            print(f"\n" + "=" * 50)
            print(f"📊 SUMMARY")
            print(f"   Collections: {len(all_results)}")
            print(f"   Total Documents: {total_documents}")
            print(f"   Total Chunks: {total_chunks}")
            
            if all_results:
                avg_chunks = total_chunks / total_documents if total_documents > 0 else 0
                print(f"   Average Chunks/Document: {avg_chunks:.1f}")
        
        print(f"\n💡 Usage:")
        print(f"   python3 inspect_collections.py                    # Inspect all collections")
        print(f"   python3 inspect_collections.py sgws               # Inspect specific collection")
        print(f"   python3 inspect_collections.py --detailed         # Show detailed document info")
        print(f"   python3 inspect_collections.py sgws --detailed    # Detailed view of specific collection")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()