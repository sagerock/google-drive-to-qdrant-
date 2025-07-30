import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

@dataclass
class CollectionConfig:
    """Configuration for a single collection upload."""
    name: str
    folders: List[str]
    qdrant_host: str
    qdrant_api_key: str
    qdrant_collection: str
    openai_api_key: Optional[str] = None
    embedding_model: str = 'text-embedding-ada-002'
    chunk_size: int = 1000
    chunk_overlap: int = 200
    include_subfolders: bool = True
    # Image analysis settings
    enable_image_analysis: bool = True
    image_analysis_model: str = 'gpt-4o'  # Updated to current model (2025)
    enable_ocr: bool = True
    ocr_language: str = 'eng'
    image_description_prompt: str = 'Describe this image in detail, including any text, charts, diagrams, or important visual elements.'

class MultiCollectionConfig:
    """Multi-collection configuration handler supporting both JSON and legacy env vars."""
    
    def __init__(self):
        self.collections: List[CollectionConfig] = []
        self.google_drive_credentials_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from JSON or fall back to legacy environment variables."""
        collections_json = os.getenv('COLLECTIONS_CONFIG')
        
        if collections_json:
            logger.info("Loading multi-collection configuration from JSON")
            self._load_from_json(collections_json)
        else:
            logger.info("Loading legacy single-collection configuration")
            self._load_legacy_config()
    
    def _load_from_json(self, collections_json: str):
        """Load configuration from JSON string."""
        try:
            config_data = json.loads(collections_json)
            collections_data = config_data.get('collections', [])
            
            for collection_data in collections_data:
                collection = CollectionConfig(
                    name=collection_data['name'],
                    folders=collection_data['folders'],
                    qdrant_host=collection_data.get('qdrant_host', os.getenv('QDRANT_HOST')),
                    qdrant_api_key=collection_data.get('qdrant_api_key', os.getenv('QDRANT_API_KEY')),
                    qdrant_collection=collection_data['qdrant_collection'],
                    openai_api_key=collection_data.get('openai_api_key', os.getenv('OPENAI_API_KEY')),
                    embedding_model=collection_data.get('embedding_model', 'text-embedding-ada-002'),
                    chunk_size=collection_data.get('chunk_size', 1000),
                    chunk_overlap=collection_data.get('chunk_overlap', 200),
                    include_subfolders=collection_data.get('include_subfolders', True),
                    # Image analysis settings
                    enable_image_analysis=collection_data.get('enable_image_analysis', True),
                    image_analysis_model=collection_data.get('image_analysis_model', 'gpt-4o'),
                    enable_ocr=collection_data.get('enable_ocr', True),
                    ocr_language=collection_data.get('ocr_language', 'eng'),
                    image_description_prompt=collection_data.get('image_description_prompt', 
                        'Describe this image in detail, including any text, charts, diagrams, or important visual elements.')
                )
                self.collections.append(collection)
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in COLLECTIONS_CONFIG: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required key in collection config: {e}")
    
    def _load_legacy_config(self):
        """Load configuration from legacy environment variables."""
        # Get folder IDs (supporting both old and new formats)
        folder_ids = []
        if os.getenv('GOOGLE_DRIVE_FOLDER_IDS'):
            folder_ids = [f.strip() for f in os.getenv('GOOGLE_DRIVE_FOLDER_IDS').split(',') if f.strip()]
        elif os.getenv('GOOGLE_DRIVE_FOLDER_ID'):
            folder_ids = [os.getenv('GOOGLE_DRIVE_FOLDER_ID')]
        
        if not folder_ids:
            raise ValueError("No Google Drive folder IDs configured")
        
        # Create single collection config from legacy env vars
        collection = CollectionConfig(
            name="default",
            folders=folder_ids,
            qdrant_host=os.getenv('QDRANT_HOST'),
            qdrant_api_key=os.getenv('QDRANT_API_KEY'),
            qdrant_collection=os.getenv('QDRANT_COLLECTION_NAME'),
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            embedding_model=os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002'),
            chunk_size=int(os.getenv('CHUNK_SIZE', 1000)),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', 200)),
            include_subfolders=os.getenv('INCLUDE_SUBFOLDERS', 'true').lower() == 'true'
        )
        
        self.collections.append(collection)
    
    def validate(self):
        """Validate that all required configuration is present."""
        if not self.google_drive_credentials_path:
            raise ValueError("Missing required environment variable: GOOGLE_DRIVE_CREDENTIALS_PATH")
        
        if not self.collections:
            raise ValueError("No collections configured")
        
        for collection in self.collections:
            self._validate_collection(collection)
        
        logger.info(f"Configuration validated successfully for {len(self.collections)} collection(s)")
        return True
    
    def _validate_collection(self, collection: CollectionConfig):
        """Validate a single collection configuration."""
        required_fields = {
            'name': collection.name,
            'folders': collection.folders,
            'qdrant_host': collection.qdrant_host,
            'qdrant_api_key': collection.qdrant_api_key,
            'qdrant_collection': collection.qdrant_collection,
            'openai_api_key': collection.openai_api_key
        }
        
        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            raise ValueError(f"Collection '{collection.name}' missing required fields: {', '.join(missing_fields)}")
        
        if not collection.folders:
            raise ValueError(f"Collection '{collection.name}' has no folders configured")

# Legacy Config class for backward compatibility
class Config:
    """Legacy configuration class for backward compatibility."""
    
    @classmethod
    def _get_multi_config(cls):
        if not hasattr(cls, '_multi_config'):
            cls._multi_config = MultiCollectionConfig()
        return cls._multi_config
    
    @classmethod
    def validate(cls):
        """Validate configuration (legacy compatibility)."""
        return cls._get_multi_config().validate()
    
    @classmethod
    @property
    def GOOGLE_DRIVE_CREDENTIALS_PATH(cls):
        return cls._get_multi_config().google_drive_credentials_path
    
    @classmethod
    @property
    def GOOGLE_DRIVE_FOLDER_IDS(cls):
        # Return folders from first collection for backward compatibility
        collections = cls._get_multi_config().collections
        return collections[0].folders if collections else []
    
    @classmethod
    @property
    def QDRANT_HOST(cls):
        collections = cls._get_multi_config().collections
        return collections[0].qdrant_host if collections else None
    
    @classmethod
    @property
    def QDRANT_API_KEY(cls):
        collections = cls._get_multi_config().collections
        return collections[0].qdrant_api_key if collections else None
    
    @classmethod
    @property
    def QDRANT_COLLECTION_NAME(cls):
        collections = cls._get_multi_config().collections
        return collections[0].qdrant_collection if collections else None
    
    @classmethod
    @property
    def OPENAI_API_KEY(cls):
        collections = cls._get_multi_config().collections
        return collections[0].openai_api_key if collections else None
    
    @classmethod
    @property
    def EMBEDDING_MODEL(cls):
        collections = cls._get_multi_config().collections
        return collections[0].embedding_model if collections else 'text-embedding-ada-002'
    
    @classmethod
    @property
    def CHUNK_SIZE(cls):
        collections = cls._get_multi_config().collections
        return collections[0].chunk_size if collections else 1000
    
    @classmethod
    @property
    def CHUNK_OVERLAP(cls):
        collections = cls._get_multi_config().collections
        return collections[0].chunk_overlap if collections else 200
    
    @classmethod
    @property
    def INCLUDE_SUBFOLDERS(cls):
        collections = cls._get_multi_config().collections
        return collections[0].include_subfolders if collections else True