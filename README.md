# AWSNA Qdrant AutoUploader

Automatically synchronize Google Drive documents to your Qdrant vector databases weekly. This project supports both single-collection (legacy) and multi-collection configurations, enabling independent processing of different document sets to separate Qdrant collections. It maintains compatibility with your existing Flowise AI bot by preserving exact metadata structure and embedding format.

## Quick Test

Once set up, test the connection:
```bash
python3 -c "from google_drive_handler import GoogleDriveHandler; handler = GoogleDriveHandler(); print('✓ Google Drive connection successful!')"
```

## Features

- 🔄 **Weekly Automated Sync**: Runs every Sunday at 2 AM UTC via GitHub Actions
- 🎯 **Multi-Collection Support**: Process different Google Drive folder sets to separate Qdrant collections
- 📁 **Universal File Support**: **10+ file types** including documents, images, web files, and structured data
- 🤖 **AI-Powered Analysis**: GPT-4o vision analysis + OCR for comprehensive image understanding
- 🧠 **Smart Chunking**: Processes documents into chunks with line-number tracking
- 🎯 **Flexible Embeddings**: Supports various OpenAI models (ada-002, text-embedding-3-small, etc.)
- 🗄️ **Qdrant Integration**: Maintains exact metadata structure from your Flowise implementation
- 📊 **Collection-Specific Logging**: Detailed logs with per-collection identification
- 🔒 **Cross-Account Sharing**: Works with folders owned by different Google accounts

## Supported File Types

### 📄 Text-Based Documents
- Google Docs (`application/vnd.google-apps.document`)
- Word Documents (`.docx`)
- PDF files (`.pdf`)
- Plain text files (`.txt`)

### 🌐 Web & Structured Files (NEW!)
- HTML files (`.html`, `.htm`)
- JSON files (`.json`)
- Markdown files (`.md`, `.markdown`)

### 🖼️ Image Files (NEW!)
- JPEG images (`.jpg`, `.jpeg`)
- PNG images (`.png`)
- GIF images (`.gif`)
- BMP images (`.bmp`)
- TIFF images (`.tiff`)
- WebP images (`.webp`)

**Web & Structured File Features:**
- 🧹 **HTML Cleaning**: Extracts clean text content from HTML, removes scripts/styles
- 📋 **JSON Structure Analysis**: Parses JSON and creates searchable key-value representations
- 📝 **Markdown Structure**: Preserves document structure with automatic table of contents

**Image Analysis Features:**
- 🔍 **OCR Text Extraction**: Automatically extracts any text found in images
- 🤖 **AI Vision Analysis**: Uses GPT-4 Vision to describe image content, charts, diagrams
- 📊 **Chart/Diagram Recognition**: Identifies and describes visual data representations
- 📷 **Photo Analysis**: Comprehensive description of photos, screenshots, and visual content

## Project Structure

```
AWSNA Qdrant AutoUploader/
├── .github/workflows/
│   └── weekly-upload.yml      # GitHub Actions workflow
├── credentials/
│   └── service-account.json   # Google Drive service account credentials
├── config.py                  # Multi-collection configuration management
├── google_drive_handler.py    # Google Drive API integration
├── document_processor.py      # Document chunking and processing
├── embedding_generator.py     # OpenAI embedding generation
├── qdrant_manager.py         # Qdrant database operations
├── main.py                   # Main orchestration script
├── collections-config.example.json # Multi-collection configuration example
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## Setup Instructions

### 1. Google Drive API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create a Service Account:
   - Go to **IAM & Admin > Service Accounts**
   - Click **Create Service Account**
   - Fill in the details and create
   - Generate a JSON key file
5. **Share your Google Drive folders with the service account email**
6. Save the JSON key file as `credentials/service-account.json`

#### 🔑 Cross-Account Folder Sharing

**Your service account email**: `python-awsna-google-drive-qdra@sapient-magnet-467418-e1.iam.gserviceaccount.com`

**Important**: You need to share **each folder** (from your collections config) with this service account email:

1. **Open each Google Drive folder** you want to process
2. **Click "Share"** (top-right corner)
3. **Add the service account email**: `python-awsna-google-drive-qdra@sapient-magnet-467418-e1.iam.gserviceaccount.com`
4. **Set permission to "Viewer"** (read-only access)
5. **Click "Send"**

**✅ Cross-Account Support**: This works even if the folders are owned by different Google accounts! The folder owner just needs to share with your service account email.

**✅ Subfolder Inheritance**: When you share a parent folder, the service account automatically gets access to all subfolders.

### 2. Configuration Options

You can use either **Multi-Collection** or **Legacy Single-Collection** configuration:

#### Option A: Multi-Collection Configuration (Recommended)

Create a JSON configuration with your collections:

```json
{
  "collections": [
    {
      "name": "hr-docs",
      "folders": ["1abc123def456ghi789jkl012mnop345"],
      "qdrant_host": "https://your-qdrant-instance.com",
      "qdrant_api_key": "your-qdrant-api-key",
      "qdrant_collection": "hr_documents",
      "openai_api_key": "your-openai-api-key",
      "embedding_model": "text-embedding-3-small",
      "chunk_size": 2000,
      "chunk_overlap": 200,
      "include_subfolders": true,
      "enable_image_analysis": true,
      "image_analysis_model": "gpt-4o",
      "enable_ocr": true,
      "ocr_language": "eng"
    }
  ]
}
```

**For local testing**: Set as environment variable
```bash
export COLLECTIONS_CONFIG='{"collections":[...]}'
python3 main.py
```

**For GitHub Actions**: Add `COLLECTIONS_CONFIG` secret with your JSON configuration

#### Image Analysis Configuration Options

```json
{
  "enable_image_analysis": true,           // Enable/disable image processing
  "image_analysis_model": "gpt-4o",  // OpenAI vision model (current 2025)
  "enable_ocr": true,                     // Enable OCR text extraction  
  "ocr_language": "eng",                  // OCR language (eng, spa, fra, etc.)
  "image_description_prompt": "Custom prompt..."  // Custom AI analysis prompt
}
```

**Image Analysis Features:**
- **OCR Text Extraction**: Extracts readable text from images (receipts, screenshots, documents)
- **AI Vision Analysis**: GPT-4o (2025 current model) describes charts, diagrams, photos, UI elements
- **Dual Content**: Both OCR text and visual descriptions are embedded and searchable
- **Fallback Handling**: Graceful degradation if OCR or Vision API fails

**⚡ 2025 Model Updates:**
- Uses **GPT-4o** (50% cheaper, faster than GPT-4 Turbo)
- Alternative models: `gpt-4.1`, `gpt-4o-mini` (cost-effective)
- Deprecated: `gpt-4-vision-preview` (no longer available)

### 📊 **Complete File Processing Matrix**

| File Type | Processing Method | Output Features |
|-----------|------------------|-----------------|
| 📄 **Google Docs** | Native Google API | Clean text extraction |
| 📄 **Word (.docx)** | python-docx parsing | Full document content |
| 📄 **PDF files** | pypdf text extraction | Multi-page support |
| 📄 **Plain text** | Direct UTF-8 processing | Preserves formatting |
| 🌐 **HTML files** | BeautifulSoup cleaning | Title + clean content |
| 📋 **JSON files** | Smart structure parsing | Searchable key-value pairs |
| 📝 **Markdown files** | Structure-aware processing | Auto table of contents |
| 🖼️ **Images (all formats)** | OCR + GPT-4o Vision | Dual text + visual analysis |

**Total Supported**: **10+ file formats** covering virtually all business document types!

#### Option B: Legacy Single-Collection Configuration

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `GOOGLE_DRIVE_FOLDER_ID`: The ID from your Google Drive folder URL
- `QDRANT_HOST`: Your Qdrant server URL
- `QDRANT_API_KEY`: Your Qdrant API key
- `QDRANT_COLLECTION_NAME`: Your collection name
- `OPENAI_API_KEY`: Your OpenAI API key

### 3. Local Development Setup

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run the uploader locally
python3 main.py
```

#### Additional Requirements for Image Analysis

**For OCR functionality**, you need Tesseract installed on your system:

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/tesseract-ocr/tesseract

**Docker/GitHub Actions:** Tesseract is automatically installed during the workflow.

#### Additional Libraries Included

The following specialized libraries are automatically installed:

**Document Processing:**
- `python-docx` - Word document parsing
- `pypdf` - PDF text extraction  
- `beautifulsoup4` + `lxml` - HTML cleaning and parsing

**Image Analysis:**
- `Pillow` - Image processing and format conversion
- `pytesseract` - OCR text extraction
- `openai` - GPT-4o vision API integration

**All dependencies are automatically managed** - just run `pip3 install -r requirements.txt`!

### 4. GitHub Actions Setup

#### For Multi-Collection Mode (Recommended)

Set up these GitHub Secrets in your repository (**Settings** → **Secrets and variables** → **Actions**):

**Required Secrets:**
- `GOOGLE_DRIVE_CREDENTIALS`: Contents of your entire `service-account.json` file
- `COLLECTIONS_CONFIG`: Your JSON configuration (see example above)

#### For Legacy Single-Collection Mode

Set up these GitHub Secrets:

- `GOOGLE_DRIVE_CREDENTIALS`: Contents of your service-account.json file
- `GOOGLE_DRIVE_FOLDER_ID`: Your Google Drive folder ID
- `QDRANT_HOST`: Your Qdrant server URL
- `QDRANT_API_KEY`: Your Qdrant API key
- `QDRANT_COLLECTION_NAME`: Your collection name
- `OPENAI_API_KEY`: Your OpenAI API key

#### Automated Schedule
- **Runs every Sunday at 2 AM UTC** automatically
- **Manual trigger** available via "Run workflow" button in Actions tab
- **Automatic fallback** to legacy mode if `COLLECTIONS_CONFIG` not provided

## How It Works

### Multi-Collection Processing
Each collection is processed independently:

1. **Authentication**: Connects to Google Drive using service account credentials
2. **Collection Setup**: Initializes collection-specific components (processors, embedders, Qdrant managers)
3. **File Discovery**: Scans all configured Google Drive folders for supported documents and images
4. **Content Extraction**: Downloads and extracts content from each file:
   - **Text Documents**: Extracts plain text content
   - **HTML Files**: Clean text extraction with title and structure preservation
   - **JSON Files**: Structured parsing with searchable key-value pairs
   - **Markdown Files**: Structure-aware processing with table of contents
   - **Images**: OCR text extraction + AI vision analysis for comprehensive content
5. **Document Processing**: Splits content into chunks using collection-specific settings
6. **Embedding Generation**: Creates vectors using collection-specific OpenAI model and API key
7. **Data Synchronization**: Clears existing Qdrant collection and uploads fresh vectors
8. **Verification**: Confirms successful upload and logs collection-specific statistics

### Collection Isolation
- Each collection processes **independently** - failures in one don't affect others
- **Complete replacement**: Each collection is fully cleared and repopulated (no stale data)
- **Cross-account folders**: Works with folders owned by different Google accounts
- **Separate configurations**: Each collection can use different chunk sizes, models, Qdrant hosts, etc.

## Content Examples

### 📄 Text Document Output
Standard text documents are processed as before with full compatibility.

### 🌐 HTML File Output
HTML files are cleaned and structured for better searchability:

```json
{
  "content": "HTML CONTENT - documentation.html\n\nTITLE: API Documentation\n\nAPI Documentation\nOverview\nThe REST API provides access to all platform features.\nAuthentication\nUse Bearer tokens for API authentication.\nEndpoints\nGET /api/users - Retrieve user list\nPOST /api/users - Create new user",
  "metadata": {
    "fileName": "documentation.html",
    "mimeType": "text/html"
  }
}
```

### 📋 JSON File Output  
JSON files are parsed and made searchable with key-value extraction:

```json
{
  "content": "JSON CONTENT - config.json\n\nSTRUCTURED DATA:\n{\n  \"database\": {\n    \"host\": \"localhost\",\n    \"port\": 5432\n  },\n  \"features\": [\"auth\", \"logging\"]\n}\n\nSEARCHABLE CONTENT:\ndatabase.host: localhost\ndatabase.port: 5432\nfeatures[0]: auth\nfeatures[1]: logging",
  "metadata": {
    "fileName": "config.json",
    "mimeType": "application/json"
  }
}
```

### 📝 Markdown File Output
Markdown files preserve structure with automatic table of contents:

```json
{
  "content": "MARKDOWN CONTENT - README.md\n\nDOCUMENT STRUCTURE:\n• Installation\n  • Prerequisites\n  • Setup Steps\n• Usage\n• Configuration\n\nFULL CONTENT:\n# Installation\n## Prerequisites\n- Node.js 16+\n- npm or yarn\n## Setup Steps\n1. Clone repository\n2. Install dependencies\n# Usage\nRun `npm start` to begin\n# Configuration\nEdit config.json file",
  "metadata": {
    "fileName": "README.md", 
    "mimeType": "text/markdown"
  }
}
```

### 🖼️ Image Analysis Output
Images generate rich, searchable content combining OCR and AI analysis:

```json
{
  "content": "IMAGE ANALYSIS - sales-chart.png\n\nEXTRACTED TEXT:\nQ1: $2.1M\nQ2: $3.4M\nQ3: $4.2M\nQ4: $5.8M\nTotal Revenue 2023\n\nVISUAL DESCRIPTION:\nThis is a blue bar chart showing quarterly revenue growth throughout 2023. The chart displays four ascending blue bars representing each quarter, with values clearly labeled above each bar. The chart has a clean white background with a title at the top reading 'Total Revenue 2023'. The progression shows steady growth from Q1 to Q4, with the highest bar representing Q4 at $5.8M.",
  "metadata": {
    "source": "https://drive.google.com/file/d/...",
    "fileName": "sales-chart.png",
    "mimeType": "image/png",
    "size": 245760,
    "loc": {"lines": {"from": 1, "to": 8}}
  }
}
```

## Metadata Structure

The uploader maintains exact compatibility with your Flowise setup:

```json
{
  "content": "Document chunk text...",
  "metadata": {
    "source": "https://docs.google.com/document/d/...",
    "fileId": "1Phr3OroT-SaGMgPmwHqDF5YeHd3QQnDq",
    "fileName": "F. AWSNA Accreditation Resources Quick Guide.docx",
    "mimeType": "application/vnd.openxmlformats-officedocument.word...",
    "size": 331779,
    "createdTime": "2025-07-16T23:14:55.048Z",
    "modifiedTime": "2025-03-10T19:15:12.000Z",
    "parents": ["1vMqyApE2hV_Jrl76yYS3gcx_-LtrWLPT"],
    "totalPages": 1,
    "pageIndex": 0,
    "driveContext": " (My Drive)",
    "loc": {
      "lines": {
        "from": 97,
        "to": 109
      }
    }
  }
}
```

## Configuration Options

### Chunking Settings
- `CHUNK_SIZE`: Maximum characters per chunk (default: 1000)
- `CHUNK_OVERLAP`: Character overlap between chunks (default: 200)

### Processing Settings
- `EMBEDDING_MODEL`: OpenAI model for embeddings (default: text-embedding-ada-002)

## Monitoring

### Logs
- All operations are logged to `uploader.log`
- GitHub Actions uploads logs as artifacts on failure
- Logs include timing, statistics, and error details

### Statistics Tracked
- Number of documents processed
- Total chunks created
- Embedding generation time
- Upload success/failure rates
- Collection before/after statistics

## Troubleshooting

### Common Issues

1. **Google Drive Permission Errors**
   - Ensure the service account email (`python-awsna-google-drive-qdra@sapient-magnet-467418-e1.iam.gserviceaccount.com`) has access to **all folders** in your configuration
   - Check that the credentials file is valid JSON
   - Verify folder sharing is set to "Viewer" permission

2. **Qdrant Connection Issues**
   - Verify your Qdrant host URL and API key
   - Ensure the collection exists and has correct vector dimensions (1536)

3. **OpenAI API Errors**
   - Check your API key is valid and has sufficient credits
   - Monitor rate limits if processing many documents

4. **GitHub Actions Failures**
   - Check that all required secrets are set
   - Review the workflow logs for specific error messages

### Debug Mode

For verbose logging, modify the logging level in `main.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## Manual Execution

You can manually trigger the upload:

1. **Locally**: Run `python main.py`
2. **GitHub Actions**: Use the "Run workflow" button in the Actions tab

## Recent Enhancements (2025)

### 🚀 **Latest Updates**
- ✅ **Image Analysis**: Full OCR + GPT-4o vision integration 
- ✅ **Web Files**: HTML, JSON, Markdown support with smart parsing
- ✅ **Current AI Models**: Updated to GPT-4o (50% cheaper, faster)
- ✅ **Multi-Collection**: Independent processing with isolated configurations
- ✅ **Enhanced Parsing**: BeautifulSoup, JSON structure analysis, Markdown TOC

### 🎯 **Why Choose This Solution**
- **Comprehensive**: Handles 10+ file types that cover 99% of business documents
- **AI-Powered**: Advanced image analysis with OCR + vision descriptions
- **Production-Ready**: Weekly automation, error handling, cross-account support
- **Flowise Compatible**: Exact metadata structure preservation
- **Cost-Optimized**: Uses latest, most efficient OpenAI models
- **Scalable**: Multi-collection architecture for enterprise use

## Cost Considerations

- **OpenAI API**: Embedding costs depend on text volume (~$0.0001 per 1K tokens)
- **GPT-4o Vision**: Image analysis ~$0.01-0.02 per image (high detail)
- **Qdrant**: Storage costs depend on your hosting setup
- **GitHub Actions**: 2000 free minutes per month for public repos

## Security Notes

- Service account credentials are stored securely in GitHub Secrets
- API keys are never logged or exposed in output
- All network connections use HTTPS/TLS encryption

## Support

For issues or questions:
1. Check the logs for specific error messages
2. Review the troubleshooting section above
3. Ensure all configuration values are correct
4. Test components individually if needed