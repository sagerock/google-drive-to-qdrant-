import logging
import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient, models
from config import Config, CollectionConfig

logger = logging.getLogger(__name__)

class QdrantManager:
    def __init__(self, collection_config: Optional[CollectionConfig] = None, 
                 qdrant_host: Optional[str] = None, 
                 qdrant_api_key: Optional[str] = None, 
                 collection_name: Optional[str] = None):
        """
        Initialize QdrantManager with collection-specific configuration.
        
        Args:
            collection_config: CollectionConfig object (preferred)
            qdrant_host: Qdrant host URL (legacy compatibility)
            qdrant_api_key: Qdrant API key (legacy compatibility) 
            collection_name: Collection name (legacy compatibility)
        """
        # Use CollectionConfig if provided, otherwise fall back to individual params or Config
        if collection_config:
            self.collection_name = collection_config.qdrant_collection
            self.collection_display_name = collection_config.name
            qdrant_url = collection_config.qdrant_host
            api_key = collection_config.qdrant_api_key
        else:
            # Legacy compatibility - use provided params or Config
            self.collection_name = collection_name or Config.QDRANT_COLLECTION_NAME
            self.collection_display_name = self.collection_name
            qdrant_url = qdrant_host or Config.QDRANT_HOST
            api_key = qdrant_api_key or Config.QDRANT_API_KEY
        
        # Handle both URL and host formats
        if qdrant_url.startswith('http://') or qdrant_url.startswith('https://'):
            # Use url parameter for full URLs
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=api_key,
                timeout=60
            )
        else:
            # Use host parameter for just hostnames
            self.client = QdrantClient(
                host=qdrant_url,
                api_key=api_key,
                timeout=60
            )
        
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify connection to Qdrant and collection exists."""
        try:
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Successfully connected to Qdrant for collection '{self.collection_display_name}'")
            
            # Check if collection exists
            collection_names = [col.name for col in collections.collections]
            if self.collection_name not in collection_names:
                logger.error(f"Collection '{self.collection_name}' ({self.collection_display_name}) not found. Available collections: {collection_names}")
                raise ValueError(f"Collection '{self.collection_name}' does not exist")
            
            # Get collection info to verify configuration
            collection_info = self.client.get_collection(self.collection_name)
            vector_size = collection_info.config.params.vectors.size
            
            if vector_size != 1536:
                logger.error(f"Collection '{self.collection_display_name}' vector size mismatch. Expected 1536, got {vector_size}")
                raise ValueError(f"Vector size mismatch: expected 1536, got {vector_size}")
            
            logger.info(f"Collection '{self.collection_display_name}' verified with correct configuration")
            
        except Exception as e:
            logger.error(f"Failed to verify Qdrant connection for '{self.collection_display_name}': {str(e)}")
            raise
    
    def clear_collection(self):
        """Clear all points from the collection."""
        try:
            # Get collection info to check current point count
            collection_info = self.client.get_collection(self.collection_name)
            current_points = collection_info.points_count
            
            if current_points == 0:
                logger.info(f"Collection '{self.collection_display_name}' is already empty")
                return
            
            logger.info(f"Clearing {current_points} points from collection '{self.collection_display_name}'")
            
            # Use scroll-based deletion since filtering requires indexes
            self._delete_all_points_by_scroll()
            
            logger.info(f"Successfully cleared collection '{self.collection_display_name}'")
            
        except Exception as e:
            logger.error(f"Error clearing collection '{self.collection_display_name}': {str(e)}")
            raise
    
    def _delete_all_points_by_scroll(self):
        """Alternative method to delete all points by scrolling through them."""
        try:
            batch_size = 1000
            offset = None
            total_deleted = 0
            
            while True:
                # Scroll through points to get their IDs
                scroll_result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=batch_size,
                    offset=offset,
                    with_payload=False,
                    with_vectors=False
                )
                
                points, next_offset = scroll_result
                
                if not points:
                    break
                
                # Extract point IDs
                point_ids = [point.id for point in points]
                
                # Delete this batch of points
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=models.PointIdsList(points=point_ids)
                )
                
                total_deleted += len(point_ids)
                logger.info(f"[{self.collection_display_name}] Deleted {len(point_ids)} points (total: {total_deleted})")
                
                # Update offset for next iteration
                offset = next_offset
                if not next_offset:
                    break
            
            logger.info(f"[{self.collection_display_name}] Finished deleting all points. Total deleted: {total_deleted}")
            
        except Exception as e:
            logger.error(f"[{self.collection_display_name}] Error in scroll-based deletion: {str(e)}")
            # Don't re-raise here as this is a fallback method
    
    def upsert_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100):
        """
        Upsert chunks to Qdrant. Each chunk should have 'content', 'metadata', and 'embedding' keys.
        """
        try:
            logger.info(f"[{self.collection_display_name}] Preparing to upsert {len(chunks)} chunks to Qdrant")
            
            # Process chunks in batches
            total_upserted = 0
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Convert chunks to Qdrant points
                points = []
                for chunk in batch:
                    point = self._create_qdrant_point(chunk)
                    if point:
                        points.append(point)
                
                if not points:
                    logger.warning(f"[{self.collection_display_name}] No valid points in batch {i//batch_size + 1}")
                    continue
                
                # Upsert the batch
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True
                )
                
                total_upserted += len(points)
                logger.info(f"[{self.collection_display_name}] Upserted batch {i//batch_size + 1}/{(len(chunks) + batch_size - 1)//batch_size} "
                           f"({len(points)} points, total: {total_upserted})")
            
            logger.info(f"[{self.collection_display_name}] Successfully upserted {total_upserted} points to Qdrant")
            
            # Verify the upsert
            self._verify_upsert(total_upserted)
            
        except Exception as e:
            logger.error(f"[{self.collection_display_name}] Error upserting chunks to Qdrant: {str(e)}")
            raise
    
    def _create_qdrant_point(self, chunk: Dict[str, Any]) -> models.PointStruct:
        """Convert a processed chunk into a Qdrant point."""
        try:
            # Generate a unique UUID for the point
            point_id = str(uuid.uuid4())
            
            # Extract the embedding
            embedding = chunk.get('embedding')
            if not embedding:
                logger.error("Chunk missing embedding")
                return None
            
            # Verify embedding dimension
            if len(embedding) != 1536:
                logger.error(f"Invalid embedding dimension: {len(embedding)}")
                return None
            
            # Create the payload matching the exact structure from the example
            payload = {
                'content': chunk.get('content', ''),
                'metadata': chunk.get('metadata', {})
            }
            
            # Create the Qdrant point
            point = models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            return point
            
        except Exception as e:
            logger.error(f"Error creating Qdrant point: {str(e)}")
            return None
    
    def _verify_upsert(self, expected_count: int):
        """Verify that the upsert was successful."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            actual_count = collection_info.points_count
            
            if actual_count == expected_count:
                logger.info(f"[{self.collection_display_name}] Upsert verification successful: {actual_count} points in collection")
            else:
                logger.warning(f"[{self.collection_display_name}] Point count mismatch: expected {expected_count}, got {actual_count}")
            
        except Exception as e:
            logger.error(f"[{self.collection_display_name}] Error verifying upsert: {str(e)}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get current collection statistics."""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            
            stats = {
                'points_count': collection_info.points_count,
                'indexed_vectors_count': collection_info.indexed_vectors_count,
                'segments_count': collection_info.segments_count,
                'status': collection_info.status,
                'optimizer_status': collection_info.optimizer_status
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"[{self.collection_display_name}] Error getting collection stats: {str(e)}")
            return {}