"""
Configuration settings for AI Document Agent
Contains API keys, printer settings, and other configuration parameters
"""

import os
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

class Config:
    """Configuration class for the AI Document Agent"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        
        # Project paths
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "data"
        self.incoming_dir = self.data_dir / "incoming"
        self.processed_dir = self.data_dir / "processed"
        self.logs_dir = self.data_dir / "logs"
        
        # Create directories if they don't exist
        for directory in [self.data_dir, self.incoming_dir, self.processed_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # AI/LLM Configuration
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "openai")  # openai, anthropic, openrouter, deepseek, groq, mock
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        self.openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229")
        # Generic model name for OpenAI-compatible providers (OpenRouter, DeepSeek, Groq)
        self.model_name: str = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
        # OpenRouter (broad model catalog including Gemini, Claude, Llama, etc.)
        self.openrouter_api_key: Optional[str] = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_base_url: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        # DeepSeek (OpenAI-compatible API)
        self.deepseek_api_key: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
        self.deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        # Groq (OpenAI-compatible API)
        self.groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
        self.groq_base_url: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "2000"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.3"))
        
        # Agent Configuration
        self.agent_name: str = os.getenv("AGENT_NAME", "AI Document Assistant")
        self.processing_instructions: str = os.getenv("PROCESSING_INSTRUCTIONS", "Improve grammar, clarity, and formatting")
        self.output_language: str = os.getenv("OUTPUT_LANGUAGE", "English")
        self.academic_style: bool = os.getenv("ACADEMIC_STYLE", "true").lower() == "true"
        self.preserve_formatting: bool = os.getenv("PRESERVE_FORMATTING", "true").lower() == "true"
        self.max_suggestions: int = int(os.getenv("MAX_SUGGESTIONS", "5"))
        
        # WhatsApp Configuration (Twilio)
        self.twilio_account_sid: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number: str = os.getenv("WHATSAPP_NUMBER", "whatsapp:+14155238886")
        self.webhook_url: Optional[str] = os.getenv("WEBHOOK_URL")
        
        # Printer Configuration
        self.printer_name: Optional[str] = os.getenv("PRINTER_NAME")
        self.default_printer: bool = os.getenv("USE_DEFAULT_PRINTER", "true").lower() == "true"
        self.print_quality: str = os.getenv("PRINT_QUALITY", "normal")  # draft, normal, high
        self.paper_size: str = os.getenv("PAPER_SIZE", "A4")
        self.duplex_printing: bool = os.getenv("DUPLEX_PRINTING", "false").lower() == "true"
        
        # Document Processing Configuration
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        self.supported_formats: list = ["pdf", "docx", "doc", "txt", "rtf"]
        self.output_format: str = os.getenv("OUTPUT_FORMAT", "pdf")
        
        # Agent Behavior Configuration
        self.auto_print: bool = os.getenv("AUTO_PRINT", "false").lower() == "true"
        self.require_confirmation: bool = os.getenv("REQUIRE_CONFIRMATION", "true").lower() == "true"
        self.max_processing_time: int = int(os.getenv("MAX_PROCESSING_TIME", "300"))  # seconds
        
        # Validation
        self._validate_config()
    
    def _validate_config(self):
        """Validate essential configuration parameters"""
        errors = []

        # Only require API keys if not using mock mode
        if self.llm_provider != "mock":
            if self.llm_provider == "openai" and not self.openai_api_key:
                errors.append("OPENAI_API_KEY must be set when using OpenAI provider")
            elif self.llm_provider == "anthropic" and not self.anthropic_api_key:
                errors.append("ANTHROPIC_API_KEY must be set when using Anthropic provider")
            elif self.llm_provider == "openrouter" and not self.openrouter_api_key:
                errors.append("OPENROUTER_API_KEY must be set when using OpenRouter provider")
            elif self.llm_provider == "deepseek" and not self.deepseek_api_key:
                errors.append("DEEPSEEK_API_KEY must be set when using DeepSeek provider")
            elif self.llm_provider == "groq" and not self.groq_api_key:
                errors.append("GROQ_API_KEY must be set when using Groq provider")
        
        # Twilio is optional for local testing
        # if not self.twilio_account_sid or not self.twilio_auth_token:
        #     errors.append("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
        
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    def get_llm_config(self) -> dict:
        """Get LLM configuration dictionary"""
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "api_key": self.openai_api_key or self.anthropic_api_key
        }
    
    def get_printer_config(self) -> dict:
        """Get printer configuration dictionary"""
        return {
            "printer_name": self.printer_name,
            "use_default": self.default_printer,
            "quality": self.print_quality,
            "paper_size": self.paper_size,
            "duplex": self.duplex_printing
        }
    
    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        return f"Config(model={self.model_name}, printer={self.printer_name or 'default'})"