import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain.text_splitter import RecursiveCharacterTextSplitter
from config import Config, CollectionConfig

logger = logging.getLogger(__name__)

class DocumentChunk:
    def __init__(self, text: str, start_line: int, end_line: int, page_index: int = 0):
        self.text = text
        self.start_line = start_line
        self.end_line = end_line
        self.page_index = page_index

class DocumentProcessor:
    def __init__(self, collection_config: Optional[CollectionConfig] = None,
                 chunk_size: Optional[int] = None,
                 chunk_overlap: Optional[int] = None):
        """
        Initialize DocumentProcessor with collection-specific configuration.
        
        Args:
            collection_config: CollectionConfig object (preferred)
            chunk_size: Chunk size (legacy compatibility)
            chunk_overlap: Chunk overlap (legacy compatibility)
        """
        if collection_config:
            self.chunk_size = collection_config.chunk_size
            self.chunk_overlap = collection_config.chunk_overlap
            self.collection_name = collection_config.name
        else:
            # Legacy compatibility
            self.chunk_size = chunk_size or Config.CHUNK_SIZE
            self.chunk_overlap = chunk_overlap or Config.CHUNK_OVERLAP
            self.collection_name = "default"
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def process_document(self, content: str, file_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process a document by splitting it into chunks and creating the full payload structure.
        Returns a list of chunks ready for Qdrant upsertion.
        """
        try:
            # Split the document into lines for line tracking
            lines = content.split('\n')
            
            # Create chunks using langchain text splitter
            chunks = self.text_splitter.split_text(content)
            
            processed_chunks = []
            current_line = 1
            
            for chunk_text in chunks:
                # Find the line range for this chunk
                start_line, end_line = self._find_line_range(chunk_text, lines, current_line)
                
                # Create the chunk with metadata matching Qdrant structure
                chunk_data = self._create_chunk_payload(
                    chunk_text, 
                    file_metadata, 
                    start_line, 
                    end_line
                )
                
                processed_chunks.append(chunk_data)
                current_line = end_line + 1
            
            logger.info(f"[{self.collection_name}] Processed {file_metadata['fileName']} into {len(processed_chunks)} chunks")
            return processed_chunks
            
        except Exception as e:
            logger.error(f"[{self.collection_name}] Error processing document {file_metadata.get('fileName', 'unknown')}: {str(e)}")
            return []
    
    def _find_line_range(self, chunk_text: str, lines: List[str], start_from_line: int) -> Tuple[int, int]:
        """
        Find the line range for a given chunk of text.
        This is a simplified approach - in production you might want more sophisticated matching.
        """
        try:
            # Count lines in the chunk
            chunk_lines = chunk_text.count('\n') + 1
            
            # Simple approach: assume sequential processing
            start_line = start_from_line
            end_line = start_line + chunk_lines - 1
            
            # Ensure we don't exceed the total number of lines
            total_lines = len(lines)
            if end_line > total_lines:
                end_line = total_lines
            
            return start_line, end_line
            
        except Exception as e:
            logger.error(f"Error finding line range for chunk: {str(e)}")
            # Return a safe default
            return start_from_line, start_from_line + 10
    
    def _create_chunk_payload(self, chunk_text: str, file_metadata: Dict[str, Any], 
                            start_line: int, end_line: int) -> Dict[str, Any]:
        """
        Create the complete payload structure for a chunk that matches the Qdrant point format.
        """
        # Create the base metadata from file metadata
        chunk_metadata = file_metadata.copy()
        
        # Add chunk-specific metadata
        chunk_metadata.update({
            'totalPages': 1,  # Assuming single page documents for now
            'pageIndex': 0,   # Starting with page 0
            'loc': {
                'lines': {
                    'from': start_line,
                    'to': end_line
                }
            }
        })
        
        # Return the complete chunk structure
        return {
            'content': chunk_text,
            'metadata': chunk_metadata
        }
    
    def process_multiple_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process multiple documents and return all chunks.
        Each document should have 'content' and 'metadata' keys.
        """
        all_chunks = []
        
        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            
            if not content:
                logger.warning(f"Skipping document with no content: {metadata.get('fileName', 'unknown')}")
                continue
            
            chunks = self.process_document(content, metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Processed {len(documents)} documents into {len(all_chunks)} total chunks")
        return all_chunks