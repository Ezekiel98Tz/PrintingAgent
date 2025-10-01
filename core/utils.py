"""
Utility functions for the AI Document Agent
Contains helper functions used across different modules
"""

import logging
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import re
import os

logger = logging.getLogger(__name__)

def setup_directories(base_path: Union[str, Path], directories: List[str]) -> Dict[str, Path]:
    """
    Create directory structure if it doesn't exist
    
    Args:
        base_path: Base directory path
        directories: List of directory names to create
        
    Returns:
        Dictionary mapping directory names to Path objects
    """
    base_path = Path(base_path)
    created_dirs = {}
    
    for dir_name in directories:
        dir_path = base_path / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        created_dirs[dir_name] = dir_path
        logger.debug(f"Ensured directory exists: {dir_path}")
    
    return created_dirs

def generate_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
    """
    Generate hash for a file
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hexadecimal hash string
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        max_length: Maximum length for the filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed_file"
    
    # Truncate if too long
    if len(sanitized) > max_length:
        name, ext = os.path.splitext(sanitized)
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"

def get_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """
    Get current timestamp as formatted string
    
    Args:
        format_str: strftime format string
        
    Returns:
        Formatted timestamp string
    """
    return datetime.now().strftime(format_str)

def save_json(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    Save data as JSON file
    
    Args:
        data: Data to save
        file_path: Path to save the file
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
        return False

def load_json(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    Load data from JSON file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Loaded data or None if error
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {e}")
        return None

def validate_phone_number(phone_number: str) -> Dict[str, Any]:
    """
    Validate and format phone number for WhatsApp
    
    Args:
        phone_number: Phone number to validate
        
    Returns:
        Dictionary with validation results
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone_number)
    
    # Check if it's a valid length (7-15 digits)
    if len(digits_only) < 7 or len(digits_only) > 15:
        return {
            "valid": False,
            "error": "Phone number must be 7-15 digits long"
        }
    
    # Add country code if missing (assume US +1 if 10 digits)
    if len(digits_only) == 10:
        digits_only = "1" + digits_only
    
    # Format for WhatsApp
    whatsapp_format = f"whatsapp:+{digits_only}"
    
    return {
        "valid": True,
        "original": phone_number,
        "digits_only": digits_only,
        "whatsapp_format": whatsapp_format,
        "international_format": f"+{digits_only}"
    }

def extract_text_preview(text: str, max_length: int = 200) -> str:
    """
    Extract a preview of text content
    
    Args:
        text: Full text content
        max_length: Maximum length of preview
        
    Returns:
        Text preview with ellipsis if truncated
    """
    if not text:
        return ""
    
    # Clean up whitespace
    cleaned_text = re.sub(r'\s+', ' ', text.strip())
    
    if len(cleaned_text) <= max_length:
        return cleaned_text
    
    # Truncate at word boundary
    truncated = cleaned_text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can find a space near the end
        truncated = truncated[:last_space]
    
    return truncated + "..."

def log_processing_event(event_type: str, data: Dict[str, Any], log_dir: Union[str, Path]) -> bool:
    """
    Log processing events to a structured log file
    
    Args:
        event_type: Type of event (e.g., "document_received", "processing_complete")
        data: Event data
        log_dir: Directory to save logs
        
    Returns:
        True if successful, False otherwise
    """
    try:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        
        # Save to daily log file
        log_file = log_dir / f"events_{get_timestamp('%Y%m%d')}.jsonl"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        return True
    except Exception as e:
        logger.error(f"Error logging event: {e}")
        return False

def retry_operation(func, max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry an operation with exponential backoff
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Initial delay between retries
        backoff: Backoff multiplier
        
    Returns:
        Function result or raises last exception
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries:
                sleep_time = delay * (backoff ** attempt)
                logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {sleep_time:.1f}s: {e}")
                time.sleep(sleep_time)
            else:
                logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
    
    raise last_exception

def clean_old_files(directory: Union[str, Path], max_age_days: int = 7, pattern: str = "*") -> Dict[str, Any]:
    """
    Clean old files from a directory
    
    Args:
        directory: Directory to clean
        max_age_days: Maximum age of files to keep
        pattern: File pattern to match
        
    Returns:
        Dictionary with cleanup results
    """
    directory = Path(directory)
    
    if not directory.exists():
        return {"success": False, "error": "Directory does not exist"}
    
    try:
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        deleted_files = []
        total_size_freed = 0
        
        for file_path in directory.glob(pattern):
            if file_path.is_file():
                file_age = current_time - file_path.stat().st_mtime
                
                if file_age > max_age_seconds:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_files.append(str(file_path))
                    total_size_freed += file_size
        
        return {
            "success": True,
            "deleted_files": deleted_files,
            "count": len(deleted_files),
            "size_freed": format_file_size(total_size_freed)
        }
        
    except Exception as e:
        logger.error(f"Error cleaning directory {directory}: {e}")
        return {"success": False, "error": str(e)}

def validate_config_values(config_dict: Dict[str, Any], required_keys: List[str]) -> Dict[str, Any]:
    """
    Validate configuration values
    
    Args:
        config_dict: Configuration dictionary
        required_keys: List of required configuration keys
        
    Returns:
        Dictionary with validation results
    """
    missing_keys = []
    empty_values = []
    
    for key in required_keys:
        if key not in config_dict:
            missing_keys.append(key)
        elif not config_dict[key]:
            empty_values.append(key)
    
    errors = []
    if missing_keys:
        errors.append(f"Missing required keys: {', '.join(missing_keys)}")
    if empty_values:
        errors.append(f"Empty values for keys: {', '.join(empty_values)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "missing_keys": missing_keys,
        "empty_values": empty_values
    }

class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.debug(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.info(f"{self.operation_name} completed in {duration:.2f} seconds")
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the operation"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None