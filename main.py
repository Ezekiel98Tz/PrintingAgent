#!/usr/bin/env python3
"""
AI Document Agent - Main Entry Point
Runs the agent loop to process documents via WhatsApp integration
"""

import logging
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import Config
from core.agent import DocumentAgent
from core.whatsapp import WhatsAppHandler
from core.document_handler import DocumentHandler
from core.printer import PrinterManager
from core.utils import setup_directories, get_timestamp
import time
import glob

def setup_logging():
    """Configure logging for the application"""
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "agent.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def run_local_mode(config, agent, logger):
    """Run in local file processing mode for testing"""
    logger.info("Running in LOCAL MODE - processing files from data/incoming/")
    
    # Initialize document handler and printer
    doc_handler = DocumentHandler(config)
    printer_manager = PrinterManager(config)
    
    # Watch for files in incoming directory
    incoming_pattern = str(config.incoming_dir / "*.docx")
    
    logger.info(f"Watching for .docx files in: {config.incoming_dir}")
    logger.info("Place .docx files in data/incoming/ to process them")
    logger.info("Press Ctrl+C to stop")
    
    try:
        while True:
            # Check for new files
            files = glob.glob(incoming_pattern)
            
            for file_path in files:
                try:
                    logger.info(f"Processing file: {file_path}")
                    process_document_pipeline(file_path, config, agent, doc_handler, printer_manager, logger)
                    
                    # Move processed file to avoid reprocessing
                    processed_file = config.processed_dir / f"original_{Path(file_path).name}"
                    Path(file_path).rename(processed_file)
                    logger.info(f"Moved original to: {processed_file}")
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
            
            # Wait before checking again
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Local mode stopped by user")

def run_whatsapp_mode(config, agent, whatsapp_handler, logger):
    """Run in WhatsApp mode (mock for now)"""
    logger.info("Running in WHATSAPP MODE (Mock)")
    logger.info("WhatsApp integration is mocked - use --local for testing")
    
    # For now, just run a simple mock
    logger.info("Mock WhatsApp server would listen for messages here...")
    logger.info("Use 'python main.py --local' to test with local files")
    
    try:
        while True:
            time.sleep(10)
            logger.info("WhatsApp mock: Waiting for messages...")
    except KeyboardInterrupt:
        logger.info("WhatsApp mode stopped by user")

def process_document_pipeline(file_path, config, agent, doc_handler, printer_manager, logger):
    """Core pipeline: Load → AI Edit → Save → Print"""
    file_path = Path(file_path)
    timestamp = get_timestamp()
    
    logger.info(f"Starting pipeline for: {file_path.name}")
    
    # Step 1: Validate and extract text from document
    logger.info("Step 1: Validating and extracting text...")
    validation = doc_handler.validate_document(file_path)
    
    if not validation["valid"]:
        raise Exception(f"Document validation failed: {validation['error']}")
    
    extraction = doc_handler.extract_text(file_path)
    if not extraction["success"]:
        raise Exception(f"Text extraction failed: {extraction['error']}")
    
    original_text = extraction["text"]
    logger.info(f"Extracted {len(original_text)} characters from document")
    
    # Step 2: AI processing
    logger.info("Step 2: Processing with AI...")
    ai_result = agent.process_document_content(original_text, "general")
    
    if not ai_result["success"]:
        raise Exception(f"AI processing failed: {ai_result['error']}")
    
    improved_text = ai_result["processed_content"]
    changes_summary = ai_result["changes_summary"]
    
    logger.info(f"AI processing complete. Changes: {changes_summary}")
    
    # Step 3: Save processed document
    logger.info("Step 3: Saving processed document...")
    output_filename = f"processed_{timestamp}_{file_path.stem}.{config.output_format}"
    
    save_result = doc_handler.save_processed_document(
        improved_text, 
        output_filename, 
        config.output_format
    )
    
    if not save_result["success"]:
        raise Exception(f"Failed to save document: {save_result['error']}")
    
    processed_file_path = save_result["file_path"]
    logger.info(f"Saved processed document: {processed_file_path}")
    
    # Step 4: Print document
    logger.info("Step 4: Printing document...")
    try:
        print_result = printer_manager.print_document(processed_file_path)
        if print_result["success"]:
            logger.info(f"Document printed successfully: {print_result['printer']}")
        else:
            logger.warning(f"Printing failed: {print_result['error']}")
    except Exception as e:
        logger.warning(f"Printing error (continuing anyway): {e}")
    
    # Step 5: Log summary
    logger.info("Step 5: Logging summary...")
    summary = {
        "timestamp": timestamp,
        "original_file": str(file_path),
        "processed_file": processed_file_path,
        "changes_summary": changes_summary,
        "original_length": len(original_text),
        "processed_length": len(improved_text),
        "model_used": ai_result.get("model_used", "unknown")
    }
    
    # Save processing log
    log_file = config.logs_dir / f"processing_{timestamp}.json"
    with open(log_file, 'w', encoding='utf-8') as f:
        import json
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Pipeline completed successfully! Log saved: {log_file}")

def main():
    """Main application entry point"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Starting AI Document Agent...")
        
        # Initialize configuration
        config = Config()
        
        # Initialize components
        agent = DocumentAgent(config)
        whatsapp_handler = WhatsAppHandler(config)
        
        # Start the agent loop
        logger.info("Agent initialized successfully. Starting main loop...")
        
        # Check if running in test mode with local files
        if len(sys.argv) > 1 and sys.argv[1] == "--local":
            run_local_mode(config, agent, logger)
        else:
            run_whatsapp_mode(config, agent, whatsapp_handler, logger)
        
        logger.info("AI Document Agent started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start AI Document Agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()