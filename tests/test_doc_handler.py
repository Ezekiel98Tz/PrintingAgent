"""
Unit tests for document_handler module
Tests document parsing, validation, and format conversion
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.document_handler import DocumentHandler
from config import Config

class TestDocumentHandler:
    """Test cases for DocumentHandler class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.supported_formats = ["pdf", "docx", "doc", "txt", "rtf"]
        config.max_file_size_mb = 10
        config.output_format = "pdf"
        config.processed_dir = Path(tempfile.gettempdir()) / "test_processed"
        config.processed_dir.mkdir(exist_ok=True)
        return config
    
    @pytest.fixture
    def doc_handler(self, mock_config):
        """Create DocumentHandler instance for testing"""
        return DocumentHandler(mock_config)
    
    @pytest.fixture
    def sample_txt_file(self):
        """Create a sample text file for testing"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a sample document for testing.\n\nIt has multiple paragraphs.")
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
    
    def test_validate_document_success(self, doc_handler, sample_txt_file):
        """Test successful document validation"""
        result = doc_handler.validate_document(sample_txt_file)
        
        assert result["valid"] is True
        assert result["format"] == "txt"
        assert "size_mb" in result
        assert result["filename"] == sample_txt_file.name
    
    def test_validate_document_file_not_exists(self, doc_handler):
        """Test validation with non-existent file"""
        result = doc_handler.validate_document("nonexistent_file.txt")
        
        assert result["valid"] is False
        assert "does not exist" in result["error"]
    
    def test_validate_document_unsupported_format(self, doc_handler):
        """Test validation with unsupported file format"""
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            result = doc_handler.validate_document(temp_path)
            assert result["valid"] is False
            assert "Unsupported format" in result["error"]
        finally:
            temp_path.unlink()
    
    def test_validate_document_too_large(self, doc_handler):
        """Test validation with file too large"""
        # Create a large file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            # Write more than 10MB of data
            large_content = "x" * (11 * 1024 * 1024)  # 11MB
            f.write(large_content.encode())
            temp_path = Path(f.name)
        
        try:
            result = doc_handler.validate_document(temp_path)
            assert result["valid"] is False
            assert "too large" in result["error"]
        finally:
            temp_path.unlink()
    
    def test_extract_text_txt_success(self, doc_handler, sample_txt_file):
        """Test successful text extraction from TXT file"""
        result = doc_handler.extract_text(sample_txt_file)
        
        assert result["success"] is True
        assert "This is a sample document" in result["text"]
        assert result["format"] == "txt"
        assert "encoding" in result
    
    def test_extract_text_invalid_file(self, doc_handler):
        """Test text extraction with invalid file"""
        result = doc_handler.extract_text("nonexistent_file.txt")
        
        assert result["success"] is False
        assert "error" in result
    
    @patch('core.document_handler.PdfReader')
    def test_extract_pdf_text_success(self, mock_pdf_reader, doc_handler):
        """Test PDF text extraction"""
        # Mock PDF reader
        mock_reader_instance = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample PDF content"
        mock_reader_instance.pages = [mock_page]
        mock_reader_instance.metadata = {"title": "Test PDF"}
        mock_pdf_reader.return_value = mock_reader_instance
        
        # Create a dummy PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"dummy pdf content")
            temp_path = Path(f.name)
        
        try:
            result = doc_handler._extract_pdf_text(temp_path)
            
            assert result["success"] is True
            assert "Sample PDF content" in result["text"]
            assert result["format"] == "pdf"
            assert result["pages"] == 1
        finally:
            temp_path.unlink()
    
    @patch('core.document_handler.Document')
    def test_extract_docx_text_success(self, mock_document, doc_handler):
        """Test DOCX text extraction"""
        # Mock Document
        mock_doc_instance = Mock()
        mock_paragraph1 = Mock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = Mock()
        mock_paragraph2.text = "Second paragraph"
        mock_doc_instance.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_document.return_value = mock_doc_instance
        
        # Create a dummy DOCX file
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            f.write(b"dummy docx content")
            temp_path = Path(f.name)
        
        try:
            result = doc_handler._extract_docx_text(temp_path)
            
            assert result["success"] is True
            assert "First paragraph" in result["text"]
            assert "Second paragraph" in result["text"]
            assert result["format"] == "docx"
            assert result["paragraphs"] == 2
        finally:
            temp_path.unlink()
    
    def test_save_processed_document_txt(self, doc_handler):
        """Test saving processed document as TXT"""
        content = "This is processed content.\n\nWith multiple paragraphs."
        original_filename = "test_document.pdf"
        
        result = doc_handler.save_processed_document(content, original_filename, "txt")
        
        assert result["success"] is True
        assert result["format"] == "txt"
        assert "file_path" in result
        
        # Verify file was created and has correct content
        saved_file = Path(result["file_path"])
        assert saved_file.exists()
        
        with open(saved_file, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        
        assert saved_content == content
        
        # Cleanup
        saved_file.unlink()
    
    @patch('core.document_handler.Document')
    def test_save_processed_document_docx(self, mock_document, doc_handler):
        """Test saving processed document as DOCX"""
        content = "This is processed content.\n\nWith multiple paragraphs."
        original_filename = "test_document.txt"
        
        # Mock Document creation
        mock_doc_instance = Mock()
        mock_document.return_value = mock_doc_instance
        
        result = doc_handler.save_processed_document(content, original_filename, "docx")
        
        assert result["success"] is True
        assert result["format"] == "docx"
        assert "file_path" in result
        
        # Verify Document methods were called
        mock_doc_instance.add_paragraph.assert_called()
        mock_doc_instance.save.assert_called_once()
    
    def test_get_document_info_success(self, doc_handler, sample_txt_file):
        """Test getting comprehensive document information"""
        result = doc_handler.get_document_info(sample_txt_file)
        
        assert result["valid"] is True
        assert result["filename"] == sample_txt_file.name
        assert result["format"] == "txt"
        assert "size_mb" in result
        assert "word_count" in result
        assert "character_count" in result
        assert "line_count" in result
        assert result["has_content"] is True
    
    def test_detect_file_format_by_extension(self, doc_handler):
        """Test file format detection by extension"""
        test_cases = [
            ("document.pdf", "pdf"),
            ("document.docx", "docx"),
            ("document.doc", "doc"),
            ("document.txt", "txt"),
            ("document.rtf", "rtf"),
        ]
        
        for filename, expected_format in test_cases:
            # Create temporary file with the extension
            with tempfile.NamedTemporaryFile(suffix=f".{expected_format}", delete=False) as f:
                temp_path = Path(f.name)
            
            try:
                detected_format = doc_handler._detect_file_format(temp_path)
                assert detected_format == expected_format
            finally:
                temp_path.unlink()

class TestDocumentHandlerIntegration:
    """Integration tests for DocumentHandler"""
    
    @pytest.fixture
    def real_config(self):
        """Create a real configuration for integration testing"""
        # Use environment variables or defaults
        config = Config()
        return config
    
    @pytest.fixture
    def integration_handler(self, real_config):
        """Create DocumentHandler with real config for integration testing"""
        return DocumentHandler(real_config)
    
    def test_full_document_processing_workflow(self, integration_handler):
        """Test complete document processing workflow"""
        # Create a sample document
        content = """
        Sample Document for Testing
        ===========================
        
        This is a test document that will be processed by the AI Document Agent.
        
        Features to test:
        - Text extraction
        - Content processing
        - File saving
        
        The document contains multiple paragraphs and formatting.
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # Step 1: Validate document
            validation = integration_handler.validate_document(temp_path)
            assert validation["valid"] is True
            
            # Step 2: Extract text
            extraction = integration_handler.extract_text(temp_path)
            assert extraction["success"] is True
            assert "Sample Document for Testing" in extraction["text"]
            
            # Step 3: Get document info
            info = integration_handler.get_document_info(temp_path)
            assert info["valid"] is True
            assert info["word_count"] > 0
            assert info["has_content"] is True
            
            # Step 4: Save processed document
            processed_content = extraction["text"] + "\n\n[Processed by AI Agent]"
            save_result = integration_handler.save_processed_document(
                processed_content, temp_path.name, "txt"
            )
            assert save_result["success"] is True
            
            # Verify saved file
            saved_file = Path(save_result["file_path"])
            assert saved_file.exists()
            
            with open(saved_file, 'r', encoding='utf-8') as f:
                saved_content = f.read()
            
            assert "[Processed by AI Agent]" in saved_content
            
            # Cleanup
            saved_file.unlink()
            
        finally:
            temp_path.unlink()

if __name__ == "__main__":
    pytest.main([__file__])