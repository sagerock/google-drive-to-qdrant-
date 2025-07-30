import logging
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import Config, CollectionConfig

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self, collection_config: Optional[CollectionConfig] = None,
                 openai_api_key: Optional[str] = None,
                 embedding_model: Optional[str] = None):
        """
        Initialize EmbeddingGenerator with collection-specific configuration.
        
        Args:
            collection_config: CollectionConfig object (preferred)
            openai_api_key: OpenAI API key (legacy compatibility)
            embedding_model: Embedding model name (legacy compatibility)
        """
        if collection_config:
            self.openai_api_key = collection_config.openai_api_key
            self.model = collection_config.embedding_model
            self.collection_name = collection_config.name
        else:
            # Legacy compatibility
            self.openai_api_key = openai_api_key or Config.OPENAI_API_KEY
            self.model = embedding_model or Config.EMBEDDING_MODEL
            self.collection_name = "default"
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.openai_api_key)
        self.max_retries = 3
        self.retry_delay = 1
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding for the given text.
        Returns a 1536-dimensional vector for text-embedding-ada-002.
        """
        for attempt in range(self.max_retries):
            try:
                # Clean the text
                text = text.replace('\n', ' ').strip()
                
                if not text:
                    logger.warning(f"[{self.collection_name}] Empty text provided for embedding")
                    return [0.0] * 1536  # Return zero vector for empty text
                
                # Generate embedding using OpenAI API
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                
                embedding = response.data[0].embedding
                
                # Verify the embedding dimension
                if len(embedding) != 1536:
                    logger.error(f"[{self.collection_name}] Unexpected embedding dimension: {len(embedding)}, expected 1536")
                    raise ValueError(f"Embedding dimension mismatch: {len(embedding)}")
                
                return embedding
                
            except Exception as e:
                logger.warning(f"[{self.collection_name}] Attempt {attempt + 1} failed for embedding generation: {str(e)}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"[{self.collection_name}] Failed to generate embedding after {self.max_retries} attempts")
                    raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        OpenAI API supports batch processing which is more efficient.
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for attempt in range(self.max_retries):
                try:
                    # Clean the texts
                    cleaned_batch = [text.replace('\n', ' ').strip() for text in batch]
                    
                    # Filter out empty texts but keep track of their positions
                    valid_texts = []
                    empty_indices = []
                    
                    for idx, text in enumerate(cleaned_batch):
                        if text:
                            valid_texts.append(text)
                        else:
                            empty_indices.append(idx)
                    
                    # Generate embeddings for valid texts
                    if valid_texts:
                        response = openai.embeddings.create(
                            model=self.model,
                            input=valid_texts
                        )
                        
                        batch_embeddings = [item.embedding for item in response.data]
                    else:
                        batch_embeddings = []
                    
                    # Insert zero vectors for empty texts
                    final_batch_embeddings = []
                    valid_idx = 0
                    
                    for idx in range(len(cleaned_batch)):
                        if idx in empty_indices:
                            final_batch_embeddings.append([0.0] * 1536)
                        else:
                            final_batch_embeddings.append(batch_embeddings[valid_idx])
                            valid_idx += 1
                    
                    embeddings.extend(final_batch_embeddings)
                    
                    logger.info(f"[{self.collection_name}] Generated embeddings for batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                    break
                    
                except Exception as e:
                    logger.warning(f"[{self.collection_name}] Batch embedding attempt {attempt + 1} failed: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay * (attempt + 1))
                    else:
                        logger.error(f"[{self.collection_name}] Failed to generate batch embeddings after {self.max_retries} attempts")
                        # Add zero vectors for this failed batch
                        embeddings.extend([[0.0] * 1536] * len(batch))
        
        logger.info(f"[{self.collection_name}] Generated {len(embeddings)} embeddings total")
        return embeddings
    
    def add_embeddings_to_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add embeddings to chunks. Each chunk should have 'content' key.
        Returns chunks with 'embedding' key added.
        """
        try:
            # Extract text content from chunks
            texts = [chunk.get('content', '') for chunk in chunks]
            
            logger.info(f"[{self.collection_name}] Generating embeddings for {len(texts)} chunks")
            
            # Generate embeddings in batches
            embeddings = self.generate_embeddings_batch(texts)
            
            # Add embeddings to chunks
            enhanced_chunks = []
            for chunk, embedding in zip(chunks, embeddings):
                enhanced_chunk = chunk.copy()
                enhanced_chunk['embedding'] = embedding
                enhanced_chunks.append(enhanced_chunk)
            
            logger.info(f"[{self.collection_name}] Successfully added embeddings to {len(enhanced_chunks)} chunks")
            return enhanced_chunks
            
        except Exception as e:
            logger.error(f"[{self.collection_name}] Error adding embeddings to chunks: {str(e)}")
            raise