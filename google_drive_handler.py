import io
import logging
from typing import List, Dict, Any, Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from config import Config

logger = logging.getLogger(__name__)

class GoogleDriveHandler:
    def __init__(self):
        self.service = self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Drive API using service account."""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                Config.GOOGLE_DRIVE_CREDENTIALS_PATH,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            service = build('drive', 'v3', credentials=credentials)
            logger.info("Successfully authenticated with Google Drive API")
            return service
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive API: {str(e)}")
            raise
    
    def get_files_from_folder(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        Fetch all files from the specified Google Drive folder.
        Returns file metadata matching the structure used in Qdrant points.
        """
        if not folder_id:
            if Config.GOOGLE_DRIVE_FOLDER_IDS:
                folder_id = Config.GOOGLE_DRIVE_FOLDER_IDS[0]  # Use first folder if none specified
            else:
                folder_id = Config.GOOGLE_DRIVE_FOLDER_ID
        
        try:
            # Query to get all files in the folder
            query = f"'{folder_id}' in parents and trashed = false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id,name,mimeType,size,createdTime,modifiedTime,parents,webViewLink)",
                pageSize=1000
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in Google Drive folder")
            
            # Process each file to match the metadata structure
            processed_files = []
            for file in files:
                processed_file = self._process_file_metadata(file)
                if processed_file:
                    processed_files.append(processed_file)
            
            return processed_files
            
        except Exception as e:
            logger.error(f"Error fetching files from Google Drive: {str(e)}")
            raise
    
    def get_files_from_multiple_folders(self, folder_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Fetch files from multiple Google Drive folders.
        Returns combined file metadata from all folders.
        """
        if not folder_ids:
            folder_ids = Config.GOOGLE_DRIVE_FOLDER_IDS
        
        if not folder_ids:
            logger.warning("No folder IDs provided")
            return []
        
        all_files = []
        
        for folder_id in folder_ids:
            folder_id = folder_id.strip()  # Remove any whitespace
            if not folder_id:
                continue
                
            try:
                logger.info(f"Fetching files from folder: {folder_id}")
                if Config.INCLUDE_SUBFOLDERS:
                    files = self.get_files_recursively(folder_id)
                else:
                    files = self.get_files_from_folder(folder_id)
                
                # Add folder context to metadata
                for file_data in files:
                    file_data['metadata']['source_folder_id'] = folder_id
                
                all_files.extend(files)
                logger.info(f"Found {len(files)} files in folder {folder_id}")
                
            except Exception as e:
                logger.error(f"Error fetching files from folder {folder_id}: {str(e)}")
                # Continue with other folders instead of failing completely
                continue
        
        logger.info(f"Total files found across all folders: {len(all_files)}")
        return all_files
    
    def get_all_subfolders(self, folder_id: str, visited: set = None) -> List[str]:
        """
        Recursively get all subfolder IDs within a given folder.
        Returns a list of folder IDs including the original folder.
        """
        if visited is None:
            visited = set()
        
        if folder_id in visited:
            return []
        
        visited.add(folder_id)
        all_folder_ids = [folder_id]
        
        try:
            # Query to find all subfolders
            query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed = false"
            
            results = self.service.files().list(
                q=query,
                fields="files(id,name)",
                pageSize=1000
            ).execute()
            
            subfolders = results.get('files', [])
            logger.info(f"Found {len(subfolders)} subfolders in {folder_id}")
            
            # Recursively get subfolders of each subfolder
            for subfolder in subfolders:
                subfolder_id = subfolder['id']
                logger.info(f"Found subfolder: {subfolder['name']} ({subfolder_id})")
                
                # Recursively get subfolders
                nested_folders = self.get_all_subfolders(subfolder_id, visited)
                all_folder_ids.extend(nested_folders)
            
            return all_folder_ids
            
        except Exception as e:
            logger.error(f"Error getting subfolders for {folder_id}: {str(e)}")
            return [folder_id]  # Return at least the original folder
    
    def get_files_recursively(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Get files from a folder and all its subfolders recursively.
        """
        if not Config.INCLUDE_SUBFOLDERS:
            # If subfolders are disabled, just get files from the main folder
            return self.get_files_from_folder(folder_id)
        
        try:
            logger.info(f"Getting all subfolders for folder: {folder_id}")
            all_folder_ids = self.get_all_subfolders(folder_id)
            logger.info(f"Found {len(all_folder_ids)} folders total (including subfolders)")
            
            all_files = []
            folder_paths = {}  # Track folder paths for better metadata
            
            # Get folder names for better tracking
            for fid in all_folder_ids:
                try:
                    folder_info = self.service.files().get(fileId=fid, fields="name,parents").execute()
                    folder_paths[fid] = folder_info.get('name', 'Unknown Folder')
                except:
                    folder_paths[fid] = 'Unknown Folder'
            
            # Get files from each folder
            for folder_id in all_folder_ids:
                try:
                    folder_name = folder_paths.get(folder_id, 'Unknown Folder')
                    logger.info(f"Processing folder: {folder_name} ({folder_id})")
                    
                    files = self.get_files_from_folder(folder_id)
                    
                    # Add folder path information to metadata
                    for file_data in files:
                        file_data['metadata']['source_folder_id'] = folder_id
                        file_data['metadata']['source_folder_name'] = folder_name
                    
                    all_files.extend(files)
                    
                    if files:
                        logger.info(f"Found {len(files)} files in folder: {folder_name}")
                    
                except Exception as e:
                    logger.error(f"Error processing folder {folder_id}: {str(e)}")
                    continue
            
            logger.info(f"Total files found recursively: {len(all_files)}")
            return all_files
            
        except Exception as e:
            logger.error(f"Error in recursive file retrieval: {str(e)}")
            # Fallback to non-recursive mode
            return self.get_files_from_folder(folder_id)
    
    def _process_file_metadata(self, file: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process raw file metadata to match Qdrant point structure."""
        try:
            # Skip files that we can't process
            supported_mime_types = [
                # Text-based documents
                'application/vnd.google-apps.document',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/pdf',
                'text/plain',
                # Web and structured text files
                'text/html',
                'application/json',
                'text/markdown',
                'text/x-markdown',
                # Image files
                'image/jpeg',
                'image/jpg', 
                'image/png',
                'image/gif',
                'image/bmp',
                'image/tiff',
                'image/webp'
            ]
            
            if file.get('mimeType') not in supported_mime_types:
                logger.warning(f"Skipping unsupported file '{file.get('name', 'unknown')}' with type: {file.get('mimeType')}")
                return None
            
            # Create metadata structure matching the Qdrant point format
            metadata = {
                'source': file.get('webViewLink', ''),
                'fileId': file.get('id', ''),
                'fileName': file.get('name', ''),
                'mimeType': file.get('mimeType', ''),
                'size': int(file.get('size', 0)) if file.get('size') else 0,
                'createdTime': file.get('createdTime', ''),
                'modifiedTime': file.get('modifiedTime', ''),
                'parents': file.get('parents', []),
                'driveContext': ' (My Drive)'  # This seems to be constant in your data
            }
            
            return {
                'file_info': file,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Error processing file metadata for {file.get('name', 'unknown')}: {str(e)}")
            return None
    
    def download_file_content(self, file_info: Dict[str, Any]) -> str:
        """Download and return the text content of a file."""
        file_id = file_info.get('id')
        mime_type = file_info.get('mimeType')
        file_name = file_info.get('name', 'unknown')
        
        try:
            if mime_type == 'application/vnd.google-apps.document':
                # Google Docs - export as plain text
                request = self.service.files().export_media(
                    fileId=file_id,
                    mimeType='text/plain'
                )
            else:
                # Other files - download directly
                request = self.service.files().get_media(fileId=file_id)
            
            # Download the content
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # Decode content based on file type
            content = file_io.getvalue()
            
            if mime_type == 'application/vnd.google-apps.document' or mime_type == 'text/plain':
                return content.decode('utf-8')
            elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                return self._extract_docx_text(content)
            elif mime_type == 'application/pdf':
                return self._extract_pdf_text(content)
            elif mime_type.startswith('image/'):
                return self._extract_image_content(content, mime_type, file_name)
            elif mime_type == 'text/html':
                return self._extract_html_text(content, file_name)
            elif mime_type == 'application/json':
                return self._extract_json_content(content, file_name)
            elif mime_type in ['text/markdown', 'text/x-markdown']:
                return self._extract_markdown_content(content, file_name)
            else:
                logger.warning(f"Unsupported mime type for content extraction: {mime_type}")
                return ""
                
        except Exception as e:
            logger.error(f"Error downloading file content for {file_name}: {str(e)}")
            return ""
    
    def _extract_docx_text(self, content: bytes) -> str:
        """Extract text from DOCX file content."""
        try:
            from docx import Document
            import io
            
            doc = Document(io.BytesIO(content))
            text_content = []
            
            for paragraph in doc.paragraphs:
                text_content.append(paragraph.text)
            
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            return ""
    
    def _extract_pdf_text(self, content: bytes) -> str:
        """Extract text from PDF file content."""
        try:
            from pypdf import PdfReader
            import io
            
            pdf_reader = PdfReader(io.BytesIO(content))
            text_content = []
            
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return '\n'.join(text_content)
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            return ""
    
    def _extract_image_content(self, content: bytes, mime_type: str, file_name: str) -> str:
        """Extract content from image files using OCR and AI vision analysis."""
        try:
            from PIL import Image
            import io
            import base64
            from openai import OpenAI
            import pytesseract
            import os
            
            # Load image
            image = Image.open(io.BytesIO(content))
            logger.info(f"Processing image: {file_name} ({image.size[0]}x{image.size[1]})")
            
            # Initialize content components
            content_parts = []
            
            # Part 1: OCR Text Extraction (if enabled)
            ocr_text = ""
            try:
                # Use OCR to extract any text from the image
                ocr_text = pytesseract.image_to_string(image, lang='eng').strip()
                if ocr_text:
                    content_parts.append(f"EXTRACTED TEXT:\n{ocr_text}")
                    logger.info(f"OCR extracted {len(ocr_text)} characters from {file_name}")
                else:
                    logger.info(f"No text found in image via OCR: {file_name}")
            except Exception as e:
                logger.warning(f"OCR extraction failed for {file_name}: {str(e)}")
            
            # Part 2: AI Vision Analysis using OpenAI GPT-4 Vision
            try:
                # Convert image to base64 for OpenAI API
                buffer = io.BytesIO()
                # Convert to RGB if necessary (for JPEG compatibility)
                if image.mode in ('RGBA', 'P'):
                    image = image.convert('RGB')
                image.save(buffer, format='JPEG', quality=85)
                base64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # Initialize OpenAI client and call Vision API (Updated to current model 2025)
                openai_api_key = os.getenv('OPENAI_API_KEY')
                if not openai_api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment")
                
                client = OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this image in detail, including any text, charts, diagrams, or important visual elements. Be comprehensive but concise."
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000
                )
                
                vision_description = response.choices[0].message.content.strip()
                if vision_description:
                    content_parts.append(f"VISUAL DESCRIPTION:\n{vision_description}")
                    logger.info(f"AI vision analysis completed for {file_name}")
                
            except Exception as e:
                logger.warning(f"AI vision analysis failed for {file_name}: {str(e)}")
                # Fallback: basic image metadata description
                content_parts.append(f"VISUAL DESCRIPTION:\nImage file: {file_name} ({image.size[0]}x{image.size[1]} pixels, {image.mode} mode)")
            
            # Combine all content parts
            if content_parts:
                final_content = f"IMAGE ANALYSIS - {file_name}\n" + "\n\n".join(content_parts)
                logger.info(f"Image analysis completed for {file_name}: {len(final_content)} characters")
                return final_content
            else:
                # Fallback content if everything fails
                return f"IMAGE FILE: {file_name} ({image.size[0]}x{image.size[1]} pixels)"
                
        except Exception as e:
            logger.error(f"Error extracting image content from {file_name}: {str(e)}")
            return f"IMAGE FILE: {file_name} (analysis failed: {str(e)})"
    
    def _extract_html_text(self, content: bytes, file_name: str) -> str:
        """Extract clean text content from HTML files."""
        try:
            from bs4 import BeautifulSoup
            
            # Decode content
            html_content = content.decode('utf-8', errors='ignore')
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract title if available
            title = soup.find('title')
            title_text = f"TITLE: {title.get_text().strip()}\n\n" if title else ""
            
            # Extract main content
            # Get text and preserve some structure
            text_content = soup.get_text(separator='\n', strip=True)
            
            # Clean up extra whitespace while preserving structure
            lines = [line.strip() for line in text_content.split('\n') if line.strip()]
            clean_content = '\n'.join(lines)
            
            final_content = f"HTML CONTENT - {file_name}\n\n{title_text}{clean_content}"
            logger.info(f"HTML extraction completed for {file_name}: {len(final_content)} characters")
            return final_content
            
        except Exception as e:
            logger.error(f"Error extracting HTML content from {file_name}: {str(e)}")
            return f"HTML FILE: {file_name} (extraction failed: {str(e)})"
    
    def _extract_json_content(self, content: bytes, file_name: str) -> str:
        """Extract and format JSON content for better searchability."""
        try:
            import json
            
            # Decode content
            json_text = content.decode('utf-8', errors='ignore')
            
            # Parse JSON to validate and format
            try:
                json_data = json.loads(json_text)
                
                # Create a searchable representation
                content_parts = [f"JSON CONTENT - {file_name}"]
                
                # Add formatted JSON for structure
                formatted_json = json.dumps(json_data, indent=2, ensure_ascii=False)
                content_parts.append(f"STRUCTURED DATA:\n{formatted_json}")
                
                # Extract key-value pairs for better searchability
                def extract_searchable_text(obj, path=""):
                    """Recursively extract searchable text from JSON object."""
                    searchable_items = []
                    
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            current_path = f"{path}.{key}" if path else key
                            if isinstance(value, (str, int, float, bool)):
                                searchable_items.append(f"{current_path}: {value}")
                            elif isinstance(value, (dict, list)):
                                searchable_items.extend(extract_searchable_text(value, current_path))
                    elif isinstance(obj, list):
                        for i, item in enumerate(obj):
                            current_path = f"{path}[{i}]"
                            if isinstance(item, (str, int, float, bool)):
                                searchable_items.append(f"{current_path}: {item}")
                            elif isinstance(item, (dict, list)):
                                searchable_items.extend(extract_searchable_text(item, current_path))
                    
                    return searchable_items
                
                searchable_text = extract_searchable_text(json_data)
                if searchable_text:
                    content_parts.append(f"SEARCHABLE CONTENT:\n" + "\n".join(searchable_text[:50]))  # Limit to first 50 items
                
                final_content = "\n\n".join(content_parts)
                logger.info(f"JSON extraction completed for {file_name}: {len(final_content)} characters")
                return final_content
                
            except json.JSONDecodeError:
                # If JSON is invalid, treat as plain text
                content_parts = [f"JSON FILE - {file_name} (Invalid JSON, treating as text)"]
                content_parts.append(f"RAW CONTENT:\n{json_text}")
                return "\n\n".join(content_parts)
                
        except Exception as e:
            logger.error(f"Error extracting JSON content from {file_name}: {str(e)}")
            return f"JSON FILE: {file_name} (extraction failed: {str(e)})"
    
    def _extract_markdown_content(self, content: bytes, file_name: str) -> str:
        """Extract content from Markdown files with structure preservation."""
        try:
            # Decode content
            markdown_text = content.decode('utf-8', errors='ignore')
            
            # Clean up the markdown content
            content_parts = [f"MARKDOWN CONTENT - {file_name}"]
            
            # Extract headers for better structure
            lines = markdown_text.split('\n')
            headers = []
            content_lines = []
            
            for line in lines:
                line = line.strip()
                if line.startswith('#'):
                    # Extract header
                    header_level = len(line) - len(line.lstrip('#'))
                    header_text = line.lstrip('#').strip()
                    headers.append(f"{'  ' * (header_level-1)}• {header_text}")
                content_lines.append(line)
            
            # Add table of contents if headers exist
            if headers:
                content_parts.append(f"DOCUMENT STRUCTURE:\n" + "\n".join(headers))
            
            # Add full markdown content
            clean_content = '\n'.join(content_lines)
            content_parts.append(f"FULL CONTENT:\n{clean_content}")
            
            final_content = "\n\n".join(content_parts)
            logger.info(f"Markdown extraction completed for {file_name}: {len(final_content)} characters")
            return final_content
            
        except Exception as e:
            logger.error(f"Error extracting Markdown content from {file_name}: {str(e)}")
            return f"MARKDOWN FILE: {file_name} (extraction failed: {str(e)})"