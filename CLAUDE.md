# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AWSNA Qdrant AutoUploader is a Python-based automation tool that synchronizes Google Drive documents to Qdrant vector databases. It supports both single-collection (legacy) and multi-collection configurations, enabling independent processing of different document sets to separate Qdrant collections. The tool maintains compatibility with existing Flowise AI bot implementations by preserving exact metadata structure and embedding format.

## Development Commands

**Note: This user prefers `python3` and `pip3` commands explicitly**

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the uploader locally
python3 main.py

# Test Google Drive connection
python3 test_connection.py

# Test individual components (for development)  
python3 -c "from google_drive_handler import GoogleDriveHandler; handler = GoogleDriveHandler()"
```

## Architecture Overview

The project follows a modular, pipeline-based architecture with clear separation of concerns:

### Core Processing Pipeline (main.py:30-149)
1. **Configuration Validation** - Ensures all required environment variables are present
2. **Component Initialization** - Creates instances of all handlers in dependency order
3. **File Discovery** - Fetches file metadata from Google Drive folder(s)
4. **Content Extraction** - Downloads and processes document content 
5. **Document Processing** - Splits into chunks with line-number tracking
6. **Embedding Generation** - Creates 1536-dimensional vectors via OpenAI API
7. **Database Operations** - Clears collection and uploads new vectors
8. **Verification** - Confirms upload success with statistics

### Component Architecture

- **config.py**: Centralized configuration with environment validation and backward compatibility for single/multiple folder IDs
- **google_drive_handler.py**: Google Drive API integration supporting multiple folder processing and recursive subfolder scanning
- **document_processor.py**: LangChain-based text chunking with precise line-number tracking for source attribution
- **embedding_generator.py**: OpenAI API integration with batch processing and retry logic
- **qdrant_manager.py**: Qdrant database operations with collection management and verification
- **main.py**: Orchestration with comprehensive logging and error handling

### Multi-Collection Architecture
The system supports two configuration modes:

**Multi-Collection Mode (JSON Configuration)**:
- Process multiple Google Drive folder sets to different Qdrant collections
- Each collection can have independent: Qdrant hosts, API keys, OpenAI keys, chunk sizes, embedding models
- Configured via `COLLECTIONS_CONFIG` environment variable with JSON format
- Enables multi-tenant scenarios, content segregation, and different processing strategies

**Legacy Single-Collection Mode**:
- Backward compatible with original environment variable configuration
- Supports both single folder (`GOOGLE_DRIVE_FOLDER_ID`) and multi-folder (`GOOGLE_DRIVE_FOLDER_IDS`) processing
- All folders processed to a single Qdrant collection
- Automatically used when `COLLECTIONS_CONFIG` is not set

## Key Technical Details

### Metadata Structure Compatibility
The uploader maintains exact compatibility with Flowise by preserving this structure:
- `content`: The text chunk
- `metadata.source`: Google Drive webViewLink URL
- `metadata.fileId`, `fileName`, `mimeType`, etc.: Google Drive file properties
- `metadata.loc.lines.from/to`: Line range tracking for precise source attribution
- `metadata.totalPages`, `pageIndex`: Document pagination info
- `metadata.driveContext`: Drive location context

### Embedding Configuration
- Model: text-embedding-ada-002 (1536 dimensions)
- Batch processing with configurable chunk sizes
- Retry logic with exponential backoff for API failures
- Zero vectors for empty/failed content to maintain consistency

### Document Processing Strategy
Uses LangChain's RecursiveCharacterTextSplitter with separators `["\n\n", "\n", " ", ""]` to maintain semantic coherence while tracking exact line ranges for each chunk.

## Configuration Options

### Multi-Collection Configuration (JSON Format)
Set `COLLECTIONS_CONFIG` environment variable with JSON configuration (see `collections-config.example.json`):

```json
{
  "collections": [
    {
      "name": "collection-name",
      "folders": ["folder_id_1", "folder_id_2"],
      "qdrant_host": "https://your-qdrant.com",
      "qdrant_api_key": "your-key",
      "qdrant_collection": "collection_name",
      "openai_api_key": "your-openai-key",
      "embedding_model": "text-embedding-ada-002",
      "chunk_size": 1000,
      "chunk_overlap": 200,
      "include_subfolders": true
    }
  ]
}
```

### Legacy Single-Collection Configuration
Required environment variables (see .env.example):
- Google Drive: `GOOGLE_DRIVE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_FOLDER_IDS` (or legacy `GOOGLE_DRIVE_FOLDER_ID`)
- Qdrant: `QDRANT_HOST`, `QDRANT_API_KEY`, `QDRANT_COLLECTION_NAME`  
- OpenAI: `OPENAI_API_KEY`
- Processing: `CHUNK_SIZE` (default: 1000), `CHUNK_OVERLAP` (default: 200)
- Options: `INCLUDE_SUBFOLDERS` (default: true)

## Automation

GitHub Actions workflow (.github/workflows/weekly-upload.yml) runs weekly (Sundays 2 AM UTC) with:
- Python 3.11 runtime
- Dependency caching for faster builds
- Secure credential handling via GitHub Secrets
- Support for both JSON multi-collection config (`COLLECTIONS_CONFIG` secret) and legacy env vars
- Log artifact upload on failures (30-day retention)
- Manual trigger capability via workflow_dispatch
- Automatic fallback to legacy mode if multi-collection config not provided

## Usage Examples

### Multi-Collection Setup
1. Create JSON configuration file or environment variable
2. Set `COLLECTIONS_CONFIG` in environment or GitHub Secrets
3. Run `python3 main.py` - will process all collections sequentially

### Legacy Single-Collection Setup  
1. Set traditional environment variables (`QDRANT_HOST`, `OPENAI_API_KEY`, etc.)
2. Do not set `COLLECTIONS_CONFIG`
3. Run `python3 main.py` - will use legacy single-collection mode

### Collection Processing Flow
Each collection is processed independently with:
- Separate component instances (DocumentProcessor, EmbeddingGenerator, QdrantManager)
- Collection-specific logging with `[collection-name]` prefixes
- Independent success/failure tracking
- Isolated error handling (one collection failure doesn't stop others)

## Error Handling Architecture

All components implement a consistent error handling pattern:
- **Graceful Degradation**: Skip problematic files rather than failing entire process
- **Structured Logging**: Collection-specific logging with clear identification
- **API Resilience**: Retry logic for rate-limited APIs with exponential backoff
- **Validation Gates**: Input validation at each pipeline stage and collection level
- **Resource Cleanup**: Proper cleanup on failures to prevent resource leaks
- **Independent Processing**: Collection failures are isolated from each other