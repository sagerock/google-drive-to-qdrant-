#!/usr/bin/env python3
"""
AWSNA Qdrant AutoUploader
Automatically sync Google Drive documents to Qdrant vector database.
"""

import logging
import sys
import time
from datetime import datetime
from typing import List, Dict, Any

from config import Config, MultiCollectionConfig
from google_drive_handler import GoogleDriveHandler
from document_processor import DocumentProcessor
from embedding_generator import EmbeddingGenerator
from qdrant_manager import QdrantManager

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('uploader.log')
        ]
    )

def process_collection(collection_config, drive_handler):
    """Process a single collection configuration."""
    logger = logging.getLogger(__name__)
    collection_start_time = time.time()
    
    logger.info("=" * 80)
    logger.info(f"PROCESSING COLLECTION: {collection_config.name}")
    logger.info(f"Folders: {len(collection_config.folders)}")
    logger.info(f"Target Collection: {collection_config.qdrant_collection}")
    logger.info("=" * 80)
    
    try:
        # Initialize collection-specific components
        logger.info(f"[{collection_config.name}] Initializing collection-specific components...")
        doc_processor = DocumentProcessor(collection_config)
        embedding_generator = EmbeddingGenerator(collection_config)
        qdrant_manager = QdrantManager(collection_config)
        logger.info(f"[{collection_config.name}] All components initialized successfully")
        
        # Get initial collection stats
        initial_stats = qdrant_manager.get_collection_stats()
        logging.info(f"[{collection_config.name}] Initial collection stats: {initial_stats}")
        
        # Step 1: Fetch files from Google Drive folders
        logger.info(f"[{collection_config.name}] Step 1: Fetching files from Google Drive...")
        if collection_config.include_subfolders:
            logger.info(f"[{collection_config.name}] Subfolder processing is enabled")
        else:
            logger.info(f"[{collection_config.name}] Subfolder processing is disabled")
        
        all_processed_files = []
        for folder_id in collection_config.folders:
            logger.info(f"[{collection_config.name}] Processing folder: {folder_id}")
            
            if collection_config.include_subfolders:
                processed_files = drive_handler.get_files_recursively(folder_id)
            else:
                processed_files = drive_handler.get_files_from_folder(folder_id)
            
            all_processed_files.extend(processed_files)
            logger.info(f"[{collection_config.name}] Found {len(processed_files)} files in folder {folder_id}")
        
        if not all_processed_files:
            logger.warning(f"[{collection_config.name}] No files found in any configured folders")
            return {"success": False, "error": "No files found"}
        
        logger.info(f"[{collection_config.name}] Total files to process: {len(all_processed_files)}")
        
        # Step 2: Download and process file contents
        logger.info(f"[{collection_config.name}] Step 2: Downloading and processing file contents...")
        documents = []
        
        for file_data in all_processed_files:
            file_info = file_data['file_info']
            metadata = file_data['metadata']
            
            logger.info(f"[{collection_config.name}] Processing file: {metadata['fileName']}")
            
            # Download file content
            content = drive_handler.download_file_content(file_info)
            
            if not content:
                logger.warning(f"[{collection_config.name}] Skipping file with no content: {metadata['fileName']}")
                continue
            
            documents.append({
                'content': content,
                'metadata': metadata
            })
        
        logger.info(f"[{collection_config.name}] Successfully downloaded content for {len(documents)} documents")
        
        # Step 3: Process documents into chunks
        logger.info(f"[{collection_config.name}] Step 3: Processing documents into chunks...")
        all_chunks = doc_processor.process_multiple_documents(documents)
        
        if not all_chunks:
            logger.error(f"[{collection_config.name}] No chunks were created from documents")
            return {"success": False, "error": "No chunks created"}
        
        logger.info(f"[{collection_config.name}] Created {len(all_chunks)} chunks from {len(documents)} documents")
        
        # Step 4: Generate embeddings
        logger.info(f"[{collection_config.name}] Step 4: Generating embeddings...")
        chunks_with_embeddings = embedding_generator.add_embeddings_to_chunks(all_chunks)
        logger.info(f"[{collection_config.name}] Generated embeddings for {len(chunks_with_embeddings)} chunks")
        
        # Step 5: Clear existing data and upsert new data
        logger.info(f"[{collection_config.name}] Step 5: Clearing existing data from Qdrant...")
        qdrant_manager.clear_collection()
        
        logger.info(f"[{collection_config.name}] Step 6: Upserting new data to Qdrant...")
        qdrant_manager.upsert_chunks(chunks_with_embeddings)
        
        # Get final collection stats
        final_stats = qdrant_manager.get_collection_stats()
        logger.info(f"[{collection_config.name}] Final collection stats: {final_stats}")
        
        # Calculate execution time for this collection
        collection_time = time.time() - collection_start_time
        
        # Collection success summary
        logger.info("=" * 80)
        logger.info(f"COLLECTION '{collection_config.name}' COMPLETED SUCCESSFULLY!")
        logger.info(f"Documents processed: {len(documents)}")
        logger.info(f"Chunks created: {len(all_chunks)}")
        logger.info(f"Points upserted: {final_stats.get('points_count', 'unknown')}")
        logger.info(f"Collection processing time: {collection_time:.2f} seconds")
        logger.info("=" * 80)
        
        return {
            "success": True,
            "collection_name": collection_config.name,
            "documents_processed": len(documents),
            "chunks_created": len(all_chunks),
            "points_upserted": final_stats.get('points_count', 0),
            "processing_time": collection_time
        }
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"COLLECTION '{collection_config.name}' FAILED!")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)
        return {"success": False, "collection_name": collection_config.name, "error": str(e)}

def main(target_collection=None):
    """Main execution function for multi-collection processing."""
    start_time = time.time()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=" * 60)
        logger.info("AWSNA Multi-Collection Qdrant AutoUploader Started")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        if target_collection:
            logger.info(f"Target collection: {target_collection}")
        logger.info("=" * 60)
        
        # Load and validate multi-collection configuration
        logger.info("Loading and validating configuration...")
        multi_config = MultiCollectionConfig()
        multi_config.validate()
        logger.info(f"Configuration validated successfully for {len(multi_config.collections)} collection(s)")
        
        # Filter collections if target specified
        collections_to_process = multi_config.collections
        if target_collection:
            collections_to_process = []
            for config in multi_config.collections:
                if (config.name == target_collection or 
                    config.qdrant_collection == target_collection):
                    collections_to_process.append(config)
                    break
            
            if not collections_to_process:
                available = [f"{config.name} ({config.qdrant_collection})" for config in multi_config.collections]
                raise ValueError(f"Collection '{target_collection}' not found. Available: {available}")
            
            logger.info(f"Processing single collection: {collections_to_process[0].name}")
        
        # Initialize shared Google Drive handler
        logger.info("Initializing Google Drive handler...")
        drive_handler = GoogleDriveHandler()
        logger.info("Google Drive handler initialized successfully")
        
        # Process each collection
        results = []
        successful_collections = 0
        failed_collections = 0
        
        for collection_config in collections_to_process:
            result = process_collection(collection_config, drive_handler)
            results.append(result)
            
            if result["success"]:
                successful_collections += 1
            else:
                failed_collections += 1
        
        # Overall execution summary
        total_time = time.time() - start_time
        
        logger.info("=" * 60)
        if target_collection:
            logger.info("SINGLE COLLECTION UPLOAD SUMMARY")
        else:
            logger.info("MULTI-COLLECTION UPLOAD SUMMARY")
        logger.info(f"Total collections processed: {len(collections_to_process)}")
        logger.info(f"Successful collections: {successful_collections}")
        logger.info(f"Failed collections: {failed_collections}")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        
        # Detailed results
        for result in results:
            if result["success"]:
                logger.info(f"✓ {result['collection_name']}: {result['documents_processed']} docs, "
                           f"{result['chunks_created']} chunks, {result['points_upserted']} points")
            else:
                logger.error(f"✗ {result['collection_name']}: {result['error']}")
        
        logger.info("=" * 60)
        
        # Exit with error if any collections failed
        if failed_collections > 0:
            raise Exception(f"{failed_collections} collection(s) failed processing")
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error("MULTI-COLLECTION UPLOAD FAILED!")
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 60)
        raise

def run_with_error_handling():
    """Run the main function with comprehensive error handling."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Check for command line argument
    target_collection = None
    if len(sys.argv) > 1:
        target_collection = sys.argv[1]
        logger.info(f"Command line argument: {target_collection}")
    
    try:
        main(target_collection)
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Upload failed with error: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    run_with_error_handling()