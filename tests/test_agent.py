"""
Unit tests for agent module
Tests AI agent logic, LLM integration, and document processing
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path
import sys
import json

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agent import DocumentAgent
from config import Config

class TestDocumentAgent:
    """Test cases for DocumentAgent class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        config = Mock(spec=Config)
        config.llm_provider = "openai"
        config.openai_api_key = "test-api-key"
        config.openai_model = "gpt-3.5-turbo"
        config.max_tokens = 2000
        config.temperature = 0.3
        config.agent_name = "AI Document Assistant"
        config.processing_instructions = "Improve grammar and clarity"
        config.output_language = "English"
        config.academic_style = True
        config.preserve_formatting = True
        config.max_suggestions = 5
        return config
    
    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing"""
        llm = Mock()
        llm.invoke = Mock()
        return llm
    
    @pytest.fixture
    def agent(self, mock_config):
        """Create DocumentAgent instance for testing"""
        with patch('core.agent.ChatOpenAI') as mock_chat_openai:
            mock_llm_instance = Mock()
            mock_chat_openai.return_value = mock_llm_instance
            
            agent = DocumentAgent(mock_config)
            agent.llm = mock_llm_instance
            return agent
    
    def test_init_with_openai_provider(self, mock_config):
        """Test initialization with OpenAI provider"""
        mock_config.llm_provider = "openai"
        
        with patch('core.agent.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_chat_openai.return_value = mock_llm
            
            agent = DocumentAgent(mock_config)
            
            mock_chat_openai.assert_called_once_with(
                api_key="test-api-key",
                model="gpt-3.5-turbo",
                max_tokens=2000,
                temperature=0.3
            )
            assert agent.llm == mock_llm
    
    def test_init_with_unsupported_provider(self, mock_config):
        """Test initialization with unsupported LLM provider"""
        mock_config.llm_provider = "unsupported_provider"
        
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            DocumentAgent(mock_config)
    
    def test_create_system_prompt(self, agent, mock_config):
        """Test system prompt creation"""
        prompt = agent._create_system_prompt()
        
        assert "AI Document Assistant" in prompt
        assert "grammar" in prompt.lower()
        assert "clarity" in prompt.lower()
        assert "academic style" in prompt.lower()
        assert "English" in prompt
        assert "preserve formatting" in prompt.lower()
    
    def test_create_processing_prompt(self, agent):
        """Test processing prompt creation"""
        document_content = "This is a sample document with some errors."
        
        prompt = agent._create_processing_prompt(document_content)
        
        assert "DOCUMENT TO PROCESS:" in prompt
        assert document_content in prompt
        assert "INSTRUCTIONS:" in prompt
        assert "RESPONSE FORMAT:" in prompt
    
    def test_parse_ai_response_valid_json(self, agent):
        """Test parsing valid AI response with JSON format"""
        ai_response = """
        {
            "improved_content": "This is an improved document with better grammar.",
            "suggestions": [
                {
                    "type": "grammar",
                    "original": "some errors",
                    "suggestion": "better grammar",
                    "explanation": "Improved clarity and correctness"
                }
            ],
            "summary": "Fixed grammar issues and improved clarity"
        }
        """
        
        result = agent._parse_ai_response(ai_response)
        
        assert result["success"] is True
        assert "improved_content" in result
        assert "suggestions" in result
        assert "summary" in result
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["type"] == "grammar"
    
    def test_parse_ai_response_invalid_json(self, agent):
        """Test parsing invalid AI response"""
        ai_response = "This is not a valid JSON response"
        
        result = agent._parse_ai_response(ai_response)
        
        assert result["success"] is False
        assert "error" in result
        assert "Failed to parse AI response" in result["error"]
    
    def test_parse_ai_response_missing_fields(self, agent):
        """Test parsing AI response with missing required fields"""
        ai_response = """
        {
            "improved_content": "This is improved content"
        }
        """
        
        result = agent._parse_ai_response(ai_response)
        
        assert result["success"] is False
        assert "error" in result
        assert "Missing required fields" in result["error"]
    
    def test_process_document_success(self, agent):
        """Test successful document processing"""
        document_content = "This document has some grammatical errors and unclear sentences."
        
        # Mock LLM response
        mock_ai_response = """
        {
            "improved_content": "This document contains grammatical errors and unclear sentences.",
            "suggestions": [
                {
                    "type": "grammar",
                    "original": "has some grammatical errors",
                    "suggestion": "contains grammatical errors",
                    "explanation": "More precise verb choice"
                }
            ],
            "summary": "Improved grammar and clarity"
        }
        """
        
        agent.llm.invoke.return_value.content = mock_ai_response
        
        result = agent.process_document(document_content)
        
        assert result["success"] is True
        assert "improved_content" in result
        assert "suggestions" in result
        assert "summary" in result
        assert "processing_time" in result
        
        # Verify LLM was called
        agent.llm.invoke.assert_called_once()
    
    def test_process_document_llm_error(self, agent):
        """Test document processing with LLM error"""
        document_content = "Test document content"
        
        # Mock LLM to raise an exception
        agent.llm.invoke.side_effect = Exception("API Error")
        
        result = agent.process_document(document_content)
        
        assert result["success"] is False
        assert "error" in result
        assert "LLM processing failed" in result["error"]
    
    def test_process_document_empty_content(self, agent):
        """Test processing empty document content"""
        result = agent.process_document("")
        
        assert result["success"] is False
        assert "error" in result
        assert "empty" in result["error"].lower()
    
    def test_process_document_with_metadata(self, agent):
        """Test document processing with metadata"""
        document_content = "Sample document content"
        metadata = {
            "filename": "test.txt",
            "format": "txt",
            "word_count": 3
        }
        
        mock_ai_response = """
        {
            "improved_content": "Sample document content with improvements.",
            "suggestions": [],
            "summary": "Minor improvements made"
        }
        """
        
        agent.llm.invoke.return_value.content = mock_ai_response
        
        result = agent.process_document(document_content, metadata)
        
        assert result["success"] is True
        assert result["metadata"] == metadata
    
    def test_suggest_improvements_only(self, agent):
        """Test getting suggestions without content modification"""
        document_content = "This document needs some improvements."
        
        mock_ai_response = """
        {
            "improved_content": "This document requires several improvements.",
            "suggestions": [
                {
                    "type": "clarity",
                    "original": "needs some improvements",
                    "suggestion": "requires several improvements",
                    "explanation": "More specific and formal language"
                }
            ],
            "summary": "Suggested improvements for clarity"
        }
        """
        
        agent.llm.invoke.return_value.content = mock_ai_response
        
        result = agent.suggest_improvements(document_content)
        
        assert result["success"] is True
        assert "suggestions" in result
        assert "summary" in result
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["type"] == "clarity"
    
    def test_get_agent_info(self, agent, mock_config):
        """Test getting agent information"""
        info = agent.get_agent_info()
        
        assert "name" in info
        assert "provider" in info
        assert "model" in info
        assert "capabilities" in info
        assert info["name"] == "AI Document Assistant"
        assert info["provider"] == "openai"
        assert info["model"] == "gpt-3.5-turbo"
    
    def test_validate_document_content_valid(self, agent):
        """Test document content validation with valid content"""
        valid_content = "This is a valid document with sufficient content for processing."
        
        result = agent._validate_document_content(valid_content)
        
        assert result["valid"] is True
        assert "word_count" in result
        assert result["word_count"] > 0
    
    def test_validate_document_content_empty(self, agent):
        """Test document content validation with empty content"""
        result = agent._validate_document_content("")
        
        assert result["valid"] is False
        assert "error" in result
        assert "empty" in result["error"].lower()
    
    def test_validate_document_content_too_short(self, agent):
        """Test document content validation with very short content"""
        short_content = "Hi"
        
        result = agent._validate_document_content(short_content)
        
        assert result["valid"] is False
        assert "error" in result
        assert "too short" in result["error"].lower()

class TestDocumentAgentIntegration:
    """Integration tests for DocumentAgent"""
    
    @pytest.fixture
    def real_config(self):
        """Create a real configuration for integration testing"""
        config = Config()
        # Override with test values if needed
        config.llm_provider = "openai"
        config.openai_api_key = "test-key"  # Use test key
        return config
    
    @pytest.fixture
    def integration_agent(self, real_config):
        """Create DocumentAgent with real config for integration testing"""
        with patch('core.agent.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_chat_openai.return_value = mock_llm
            return DocumentAgent(real_config)
    
    def test_full_processing_workflow(self, integration_agent):
        """Test complete document processing workflow"""
        # Sample document with various issues
        document_content = """
        Student Essay Draft
        
        this essay is about climate change and its affects on the environment. 
        The problem is very serious and we need to do something about it quick.
        
        There are many causes of climate change such as:
        - burning fossil fuels
        - deforestation 
        - industrial processes
        
        In conclusion, climate change is a big problem that effects everyone.
        """
        
        # Mock AI response
        mock_response = """
        {
            "improved_content": "Student Essay Draft\\n\\nThis essay examines climate change and its effects on the environment. The problem is extremely serious, and immediate action is required.\\n\\nThere are several primary causes of climate change, including:\\n- Burning fossil fuels\\n- Deforestation\\n- Industrial processes\\n\\nIn conclusion, climate change is a significant problem that affects everyone.",
            "suggestions": [
                {
                    "type": "grammar",
                    "original": "affects",
                    "suggestion": "effects",
                    "explanation": "Incorrect word usage - should be 'effects' as a noun"
                },
                {
                    "type": "style",
                    "original": "quick",
                    "suggestion": "immediately",
                    "explanation": "More formal and precise language"
                },
                {
                    "type": "grammar",
                    "original": "effects everyone",
                    "suggestion": "affects everyone",
                    "explanation": "Should use 'affects' as a verb"
                }
            ],
            "summary": "Corrected grammar errors, improved formality, and enhanced clarity throughout the essay."
        }
        """
        
        integration_agent.llm.invoke.return_value.content = mock_response
        
        # Process the document
        result = integration_agent.process_document(document_content)
        
        # Verify results
        assert result["success"] is True
        assert "improved_content" in result
        assert "suggestions" in result
        assert "summary" in result
        assert len(result["suggestions"]) == 3
        
        # Check that improvements were made
        improved_content = result["improved_content"]
        assert "This essay examines" in improved_content
        assert "extremely serious" in improved_content
        assert "affects everyone" in improved_content
    
    def test_suggestion_only_workflow(self, integration_agent):
        """Test suggestion-only workflow without content modification"""
        document_content = "The quick brown fox jumps over the lazy dog."
        
        mock_response = """
        {
            "improved_content": "The quick brown fox leaps over the lazy dog.",
            "suggestions": [
                {
                    "type": "style",
                    "original": "jumps",
                    "suggestion": "leaps",
                    "explanation": "More elegant verb choice"
                }
            ],
            "summary": "Minor stylistic improvement suggested."
        }
        """
        
        integration_agent.llm.invoke.return_value.content = mock_response
        
        # Get suggestions only
        result = integration_agent.suggest_improvements(document_content)
        
        assert result["success"] is True
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["type"] == "style"
        assert "leaps" in result["suggestions"][0]["suggestion"]

class TestDocumentAgentPerformance:
    """Performance and stress tests for DocumentAgent"""
    
    @pytest.fixture
    def performance_agent(self, mock_config):
        """Create agent for performance testing"""
        with patch('core.agent.ChatOpenAI') as mock_chat_openai:
            mock_llm = Mock()
            mock_chat_openai.return_value = mock_llm
            return DocumentAgent(mock_config)
    
    def test_large_document_processing(self, performance_agent):
        """Test processing of large documents"""
        # Create a large document (simulate a long essay)
        large_content = """
        Introduction to Artificial Intelligence
        
        """ + "This is a paragraph about AI and machine learning. " * 100
        
        mock_response = """
        {
            "improved_content": "Improved large document content...",
            "suggestions": [
                {
                    "type": "clarity",
                    "original": "repetitive content",
                    "suggestion": "varied content",
                    "explanation": "Reduce repetition"
                }
            ],
            "summary": "Processed large document successfully"
        }
        """
        
        performance_agent.llm.invoke.return_value.content = mock_response
        
        result = performance_agent.process_document(large_content)
        
        assert result["success"] is True
        assert "processing_time" in result
        # Verify it can handle large content
        assert len(large_content) > 1000

if __name__ == "__main__":
    pytest.main([__file__])