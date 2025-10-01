"""
AI Agent Logic for Document Processing
Handles the main AI/LLM integration using LangChain
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

try:
    from langchain.llms import OpenAI
    from langchain.chat_models import ChatOpenAI
    from langchain.schema import HumanMessage, SystemMessage
    from langchain.prompts import PromptTemplate
except ImportError:
    # Fallback for different langchain versions
    pass

from config import Config
import json
import time

logger = logging.getLogger(__name__)

class MockLLM:
    """Mock LLM for testing without API keys"""
    
    def invoke(self, messages):
        """Mock invoke method that returns a realistic response"""
        # Simulate processing time
        time.sleep(1)
        
        # Extract content from messages
        if isinstance(messages, list):
            content = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        else:
            content = str(messages)
        
        # Generate mock response
        mock_response = {
            "improved_content": self._improve_text_mock(content),
            "suggestions": [
                {
                    "type": "grammar",
                    "original": "example text",
                    "suggestion": "improved example text",
                    "explanation": "Mock improvement for testing"
                },
                {
                    "type": "clarity",
                    "original": "unclear phrase",
                    "suggestion": "clearer phrase",
                    "explanation": "Enhanced clarity for better understanding"
                }
            ],
            "summary": "Mock AI processing completed. Document has been improved for grammar and clarity."
        }
        
        class MockResponse:
            def __init__(self, content):
                self.content = json.dumps(content, indent=2)
        
        return MockResponse(mock_response)
    
    def _improve_text_mock(self, original_text):
        """Simple mock text improvement"""
        # Basic improvements for demonstration
        improved = original_text.replace(" i ", " I ")
        improved = improved.replace("dont", "don't")
        improved = improved.replace("cant", "can't")
        improved = improved.replace("wont", "won't")
        improved = improved.replace("  ", " ")  # Remove double spaces
        
        # Add a note that this was processed
        if len(improved.strip()) > 0:
            improved += "\n\n[Document processed by AI Assistant - Mock Mode]"
        
        return improved

class DocumentAgent:
    """AI Agent for processing and improving documents"""
    
    def __init__(self, config: Config):
        """Initialize the document agent with configuration"""
        self.config = config
        self.llm = self._initialize_llm()
        self.system_prompt = self._get_system_prompt()
        
    def _initialize_llm(self):
        """Initialize the language model based on configuration"""
        try:
            if self.config.llm_provider == "mock":
                logger.info("Using mock LLM for testing")
                return MockLLM()
            elif self.config.llm_provider == "openai" and self.config.openai_api_key:
                logger.info(f"Initializing OpenAI LLM: {self.config.openai_model}")
                return ChatOpenAI(
                    api_key=self.config.openai_api_key,
                    model=self.config.openai_model,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            else:
                logger.warning("No supported LLM configuration found")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for document processing"""
        return """You are an AI assistant specialized in improving and formatting documents for students. 
        Your tasks include:
        
        1. **Grammar and Spelling**: Correct any grammatical errors and spelling mistakes
        2. **Formatting**: Improve document structure, headings, and layout
        3. **Clarity**: Enhance readability and clarity of the content
        4. **Academic Style**: Ensure the document follows proper academic writing conventions
        5. **Consistency**: Maintain consistent formatting and style throughout
        
        Guidelines:
        - Preserve the original meaning and intent of the document
        - Keep the author's voice and style while improving clarity
        - Add proper headings and structure if missing
        - Ensure proper citation format if references are present
        - Maintain the original language of the document
        
        Always provide a brief summary of the changes made at the end."""
    
    def process_document_content(self, content: str, document_type: str = "general") -> Dict[str, Any]:
        """
        Process document content using AI
        
        Args:
            content: The text content of the document
            document_type: Type of document (essay, report, assignment, etc.)
            
        Returns:
            Dictionary containing processed content and metadata
        """
        if not self.llm:
            logger.error("LLM not initialized, cannot process document")
            return {
                "success": False,
                "error": "AI model not available",
                "original_content": content
            }
        
        try:
            # Create the processing prompt
            prompt = self._create_processing_prompt(content, document_type)
            
            # Process with LLM
            if isinstance(self.llm, MockLLM):
                # Mock LLM
                response = self.llm.invoke(prompt)
                processed_content = response.content
            elif hasattr(self.llm, 'invoke'):
                # Modern LangChain interface
                try:
                    from langchain.schema import HumanMessage, SystemMessage
                    messages = [
                        SystemMessage(content=self.system_prompt),
                        HumanMessage(content=prompt)
                    ]
                    response = self.llm.invoke(messages)
                    processed_content = response.content
                except ImportError:
                    # Fallback to string input
                    full_prompt = f"{self.system_prompt}\n\n{prompt}"
                    response = self.llm.invoke(full_prompt)
                    processed_content = response.content if hasattr(response, 'content') else str(response)
            else:
                # Legacy LangChain interface
                full_prompt = f"{self.system_prompt}\n\n{prompt}"
                processed_content = self.llm.predict(full_prompt)
            
            # Extract the processed content and summary
            result = self._parse_ai_response(processed_content)
            
            return {
                "success": True,
                "original_content": content,
                "processed_content": result["content"],
                "changes_summary": result["summary"],
                "document_type": document_type,
                "model_used": getattr(self.config, 'openai_model', 'mock') if hasattr(self.config, 'openai_model') else 'mock'
            }
            
        except Exception as e:
            logger.error(f"Error processing document with AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_content": content
            }
    
    def _create_processing_prompt(self, content: str, document_type: str) -> str:
        """Create a specific prompt for document processing"""
        prompt_template = """
        Please improve the following {document_type} document. Focus on:
        - Grammar and spelling corrections
        - Better formatting and structure
        - Enhanced clarity and readability
        - Academic writing standards
        
        Document to improve:
        ---
        {content}
        ---
        
        Please provide:
        1. The improved document
        2. A brief summary of changes made
        
        Format your response as:
        IMPROVED DOCUMENT:
        [Your improved version here]
        
        CHANGES SUMMARY:
        [Brief summary of what you changed]
        """
        
        return prompt_template.format(
            document_type=document_type,
            content=content
        )
    
    def _parse_ai_response(self, response: str) -> Dict[str, str]:
        """Parse the AI response to extract content and summary"""
        try:
            # Split the response into content and summary
            if "IMPROVED DOCUMENT:" in response and "CHANGES SUMMARY:" in response:
                parts = response.split("CHANGES SUMMARY:")
                content_part = parts[0].replace("IMPROVED DOCUMENT:", "").strip()
                summary_part = parts[1].strip() if len(parts) > 1 else "Document processed successfully"
            else:
                # Fallback if format is not followed
                content_part = response.strip()
                summary_part = "Document processed and improved"
            
            return {
                "content": content_part,
                "summary": summary_part
            }
        except Exception as e:
            logger.warning(f"Error parsing AI response: {e}")
            return {
                "content": response,
                "summary": "Document processed"
            }
    
    def suggest_improvements(self, content: str) -> Dict[str, Any]:
        """
        Suggest improvements without making changes
        
        Args:
            content: The document content to analyze
            
        Returns:
            Dictionary containing suggestions
        """
        if not self.llm:
            return {"success": False, "error": "AI model not available"}
        
        try:
            prompt = f"""
            Please analyze the following document and provide specific suggestions for improvement.
            Do not rewrite the document, just provide actionable feedback.
            
            Document:
            ---
            {content}
            ---
            
            Please provide suggestions in these categories:
            1. Grammar and Language
            2. Structure and Organization
            3. Clarity and Readability
            4. Academic Style
            5. Formatting
            """
            
            if hasattr(self.llm, 'predict_messages'):
                messages = [HumanMessage(content=prompt)]
                response = self.llm.predict_messages(messages)
                suggestions = response.content
            else:
                suggestions = self.llm.predict(prompt)
            
            return {
                "success": True,
                "suggestions": suggestions,
                "model_used": self.config.model_name
            }
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return {
                "success": False,
                "error": str(e)
            }