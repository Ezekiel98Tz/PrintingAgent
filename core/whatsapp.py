"""
WhatsApp Integration Module
Handles WhatsApp API integration using Twilio for receiving and sending messages
"""

import logging
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import mimetypes

try:
    from twilio.rest import Client
    from twilio.twiml.messaging_response import MessagingResponse
except ImportError:
    Client = None
    MessagingResponse = None

try:
    from flask import Flask, request, Response
except ImportError:
    Flask = None

from config import Config

logger = logging.getLogger(__name__)

class WhatsAppHandler:
    """Handles WhatsApp messaging through Twilio API"""
    
    def __init__(self, config: Config):
        """Initialize WhatsApp handler with Twilio configuration"""
        self.config = config
        self.client = self._initialize_twilio_client()
        self.webhook_app = None
        
    def _initialize_twilio_client(self):
        """Initialize Twilio client"""
        if not Client:
            logger.error("Twilio library not available")
            return None
            
        if not self.config.twilio_account_sid or not self.config.twilio_auth_token:
            logger.error("Twilio credentials not configured")
            return None
            
        try:
            client = Client(self.config.twilio_account_sid, self.config.twilio_auth_token)
            # Test the connection
            client.api.accounts(self.config.twilio_account_sid).fetch()
            logger.info("Twilio client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            return None
    
    def send_message(self, to_number: str, message: str, media_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a WhatsApp message
        
        Args:
            to_number: Recipient's WhatsApp number (format: whatsapp:+1234567890)
            message: Text message to send
            media_url: Optional URL to media file
            
        Returns:
            Dictionary with send results
        """
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            # Ensure number is in WhatsApp format
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            # Prepare message parameters
            message_params = {
                "from_": self.config.whatsapp_number,
                "to": to_number,
                "body": message
            }
            
            if media_url:
                message_params["media_url"] = [media_url]
            
            # Send message
            message_obj = self.client.messages.create(**message_params)
            
            return {
                "success": True,
                "message_sid": message_obj.sid,
                "status": message_obj.status,
                "to": to_number,
                "from": self.config.whatsapp_number
            }
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return {"success": False, "error": str(e)}
    
    def download_media(self, media_url: str, media_content_type: str) -> Dict[str, Any]:
        """
        Download media file from WhatsApp message
        
        Args:
            media_url: URL to the media file
            media_content_type: MIME type of the media
            
        Returns:
            Dictionary with download results and local file path
        """
        try:
            # Determine file extension from content type
            extension = mimetypes.guess_extension(media_content_type) or '.bin'
            
            # Download the file
            response = requests.get(media_url, timeout=30)
            response.raise_for_status()
            
            # Save to incoming directory
            filename = f"whatsapp_media_{Path().cwd().name}{extension}"  # Simple timestamp
            file_path = self.config.incoming_dir / filename
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "size_bytes": len(response.content),
                "content_type": media_content_type
            }
            
        except Exception as e:
            logger.error(f"Failed to download media: {e}")
            return {"success": False, "error": str(e)}
    
    def process_incoming_message(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming WhatsApp message from webhook
        
        Args:
            webhook_data: Data received from Twilio webhook
            
        Returns:
            Dictionary with processed message information
        """
        try:
            message_info = {
                "from": webhook_data.get("From", ""),
                "to": webhook_data.get("To", ""),
                "body": webhook_data.get("Body", ""),
                "message_sid": webhook_data.get("MessageSid", ""),
                "num_media": int(webhook_data.get("NumMedia", 0)),
                "media_files": []
            }
            
            # Process media attachments
            if message_info["num_media"] > 0:
                for i in range(message_info["num_media"]):
                    media_url = webhook_data.get(f"MediaUrl{i}")
                    media_content_type = webhook_data.get(f"MediaContentType{i}")
                    
                    if media_url and media_content_type:
                        download_result = self.download_media(media_url, media_content_type)
                        if download_result["success"]:
                            message_info["media_files"].append(download_result)
                        else:
                            logger.error(f"Failed to download media {i}: {download_result['error']}")
            
            return {
                "success": True,
                "message": message_info
            }
            
        except Exception as e:
            logger.error(f"Error processing incoming message: {e}")
            return {"success": False, "error": str(e)}
    
    def create_webhook_response(self, response_message: str) -> str:
        """
        Create TwiML response for webhook
        
        Args:
            response_message: Message to send back
            
        Returns:
            TwiML XML string
        """
        if not MessagingResponse:
            return f"<Response><Message>{response_message}</Message></Response>"
        
        try:
            resp = MessagingResponse()
            resp.message(response_message)
            return str(resp)
        except Exception as e:
            logger.error(f"Error creating webhook response: {e}")
            return f"<Response><Message>Error processing request</Message></Response>"
    
    def setup_webhook_server(self, port: int = 5000) -> Optional[Flask]:
        """
        Set up Flask webhook server for receiving WhatsApp messages
        
        Args:
            port: Port to run the webhook server on
            
        Returns:
            Flask app instance or None if Flask not available
        """
        if not Flask:
            logger.error("Flask not available for webhook server")
            return None
        
        app = Flask(__name__)
        
        @app.route("/webhook", methods=["POST"])
        def webhook():
            """Handle incoming WhatsApp messages"""
            try:
                # Process the incoming message
                webhook_data = dict(request.form)
                result = self.process_incoming_message(webhook_data)
                
                if result["success"]:
                    message_info = result["message"]
                    
                    # Log the received message
                    logger.info(f"Received WhatsApp message from {message_info['from']}: {message_info['body']}")
                    
                    # TODO: Integrate with document processing pipeline
                    # For now, send a simple acknowledgment
                    if message_info["media_files"]:
                        response_msg = f"Received {len(message_info['media_files'])} file(s). Processing..."
                    else:
                        response_msg = "Message received. How can I help you with document processing?"
                    
                    twiml_response = self.create_webhook_response(response_msg)
                    return Response(twiml_response, mimetype="text/xml")
                else:
                    error_response = self.create_webhook_response("Sorry, there was an error processing your message.")
                    return Response(error_response, mimetype="text/xml")
                    
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                error_response = self.create_webhook_response("Sorry, there was an error processing your message.")
                return Response(error_response, mimetype="text/xml")
        
        @app.route("/health", methods=["GET"])
        def health():
            """Health check endpoint"""
            return {"status": "healthy", "service": "whatsapp-webhook"}
        
        self.webhook_app = app
        return app
    
    def send_document_confirmation(self, to_number: str, document_info: Dict[str, Any], 
                                 processing_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send confirmation message about document processing
        
        Args:
            to_number: Recipient's WhatsApp number
            document_info: Information about the processed document
            processing_result: Results from AI processing
            
        Returns:
            Dictionary with send results
        """
        try:
            # Create confirmation message
            message = f"""📄 Document Processed Successfully!

📋 Original: {document_info.get('filename', 'Unknown')}
📊 Format: {document_info.get('format', 'Unknown')}
📏 Size: {document_info.get('size_mb', 0):.1f} MB

🤖 AI Processing:
{processing_result.get('changes_summary', 'Document has been improved and formatted.')}

✅ Status: Ready for printing
🖨️ Printer: {self.config.printer_name or 'Default printer'}

The document has been processed and sent to the printer."""
            
            return self.send_message(to_number, message)
            
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}")
            return {"success": False, "error": str(e)}
    
    def send_error_notification(self, to_number: str, error_message: str) -> Dict[str, Any]:
        """
        Send error notification to user
        
        Args:
            to_number: Recipient's WhatsApp number
            error_message: Error message to send
            
        Returns:
            Dictionary with send results
        """
        message = f"""❌ Processing Error

Sorry, there was an issue processing your document:

{error_message}

Please try again or contact support if the problem persists."""
        
        return self.send_message(to_number, message)
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get Twilio account information"""
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            account = self.client.api.accounts(self.config.twilio_account_sid).fetch()
            return {
                "success": True,
                "account_sid": account.sid,
                "friendly_name": account.friendly_name,
                "status": account.status,
                "type": account.type
            }
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {"success": False, "error": str(e)}
    
    def list_messages(self, limit: int = 20) -> Dict[str, Any]:
        """
        List recent WhatsApp messages
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            Dictionary with message list
        """
        if not self.client:
            return {"success": False, "error": "Twilio client not initialized"}
        
        try:
            messages = self.client.messages.list(limit=limit)
            
            message_list = []
            for msg in messages:
                message_list.append({
                    "sid": msg.sid,
                    "from": msg.from_,
                    "to": msg.to,
                    "body": msg.body,
                    "status": msg.status,
                    "direction": msg.direction,
                    "date_created": msg.date_created.isoformat() if msg.date_created else None
                })
            
            return {
                "success": True,
                "messages": message_list,
                "count": len(message_list)
            }
            
        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return {"success": False, "error": str(e)}