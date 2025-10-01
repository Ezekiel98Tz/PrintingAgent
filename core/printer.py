"""
Printer Integration Module
Handles sending documents to local printers with various configuration options
"""

import logging
import platform
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import tempfile
import os

# Platform-specific imports
if platform.system() == "Windows":
    try:
        import win32print
        import win32api
    except ImportError:
        win32print = None
        win32api = None
elif platform.system() == "Linux":
    try:
        import cups
    except ImportError:
        cups = None

from config import Config

logger = logging.getLogger(__name__)

class PrinterManager:
    """Manages printer operations and configuration"""
    
    def __init__(self, config: Config):
        """Initialize printer manager with configuration"""
        self.config = config
        self.system = platform.system()
        self.available_printers = self._get_available_printers()
        
    def _get_available_printers(self) -> List[Dict[str, Any]]:
        """Get list of available printers on the system"""
        printers = []
        
        try:
            if self.system == "Windows" and win32print:
                printers = self._get_windows_printers()
            elif self.system == "Linux" and cups:
                printers = self._get_linux_printers()
            else:
                # Fallback: try to get printers via system commands
                printers = self._get_printers_fallback()
                
        except Exception as e:
            logger.error(f"Error getting available printers: {e}")
            
        return printers
    
    def _get_windows_printers(self) -> List[Dict[str, Any]]:
        """Get Windows printers using win32print"""
        printers = []
        
        try:
            printer_list = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
            
            for printer in printer_list:
                printer_name = printer[2]  # Printer name is at index 2
                
                # Get printer info
                try:
                    handle = win32print.OpenPrinter(printer_name)
                    printer_info = win32print.GetPrinter(handle, 2)
                    win32print.ClosePrinter(handle)
                    
                    printers.append({
                        "name": printer_name,
                        "driver": printer_info.get("pDriverName", "Unknown"),
                        "port": printer_info.get("pPortName", "Unknown"),
                        "status": "Available",
                        "is_default": printer_name == win32print.GetDefaultPrinter()
                    })
                except Exception as e:
                    logger.warning(f"Could not get info for printer {printer_name}: {e}")
                    printers.append({
                        "name": printer_name,
                        "status": "Unknown",
                        "is_default": False
                    })
                    
        except Exception as e:
            logger.error(f"Error getting Windows printers: {e}")
            
        return printers
    
    def _get_linux_printers(self) -> List[Dict[str, Any]]:
        """Get Linux printers using CUPS"""
        printers = []
        
        try:
            conn = cups.Connection()
            printer_dict = conn.getPrinters()
            
            for printer_name, printer_info in printer_dict.items():
                printers.append({
                    "name": printer_name,
                    "description": printer_info.get("printer-info", ""),
                    "location": printer_info.get("printer-location", ""),
                    "status": printer_info.get("printer-state-message", "Available"),
                    "is_default": printer_name == conn.getDefault()
                })
                
        except Exception as e:
            logger.error(f"Error getting Linux printers: {e}")
            
        return printers
    
    def _get_printers_fallback(self) -> List[Dict[str, Any]]:
        """Fallback method to get printers using system commands"""
        printers = []
        
        try:
            if self.system == "Windows":
                # Use PowerShell to get printers
                result = subprocess.run(
                    ["powershell", "-Command", "Get-Printer | Select-Object Name, DriverName, PortName"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[2:]  # Skip header
                    for line in lines:
                        if line.strip():
                            parts = line.split()
                            if parts:
                                printers.append({
                                    "name": parts[0],
                                    "status": "Available",
                                    "is_default": False
                                })
            elif self.system == "Linux":
                # Use lpstat to get printers
                result = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith("printer"):
                            parts = line.split()
                            if len(parts) >= 2:
                                printers.append({
                                    "name": parts[1],
                                    "status": "Available",
                                    "is_default": False
                                })
                                
        except Exception as e:
            logger.error(f"Error in printer fallback method: {e}")
            
        return printers
    
    def get_default_printer(self) -> Optional[str]:
        """Get the default printer name"""
        try:
            if self.system == "Windows" and win32print:
                return win32print.GetDefaultPrinter()
            elif self.system == "Linux" and cups:
                conn = cups.Connection()
                return conn.getDefault()
            else:
                # Find default from available printers
                for printer in self.available_printers:
                    if printer.get("is_default", False):
                        return printer["name"]
        except Exception as e:
            logger.error(f"Error getting default printer: {e}")
            
        return None
    
    def print_document(self, file_path: Union[str, Path], printer_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Print a document to the specified printer
        
        Args:
            file_path: Path to the document to print
            printer_name: Name of the printer (uses default if None)
            
        Returns:
            Dictionary with print job results
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {"success": False, "error": "File does not exist"}
        
        # Determine printer to use
        target_printer = printer_name or self.config.printer_name
        if not target_printer and self.config.default_printer:
            target_printer = self.get_default_printer()
        
        if not target_printer:
            return {"success": False, "error": "No printer specified and no default printer found"}
        
        # Validate printer exists
        printer_names = [p["name"] for p in self.available_printers]
        if target_printer not in printer_names:
            return {
                "success": False, 
                "error": f"Printer '{target_printer}' not found. Available: {', '.join(printer_names)}"
            }
        
        try:
            if self.system == "Windows":
                return self._print_windows(file_path, target_printer)
            elif self.system == "Linux":
                return self._print_linux(file_path, target_printer)
            else:
                return {"success": False, "error": f"Printing not supported on {self.system}"}
                
        except Exception as e:
            logger.error(f"Error printing document: {e}")
            return {"success": False, "error": str(e)}
    
    def _print_windows(self, file_path: Path, printer_name: str) -> Dict[str, Any]:
        """Print document on Windows"""
        try:
            if win32print and win32api:
                # Use win32api to print
                win32api.ShellExecute(
                    0,
                    "print",
                    str(file_path),
                    f'/d:"{printer_name}"',
                    ".",
                    0
                )
                return {
                    "success": True,
                    "printer": printer_name,
                    "file": str(file_path),
                    "method": "win32api"
                }
            else:
                # Fallback to system command
                result = subprocess.run([
                    "powershell", "-Command",
                    f'Start-Process -FilePath "{file_path}" -Verb Print -ArgumentList "/d:{printer_name}"'
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "printer": printer_name,
                        "file": str(file_path),
                        "method": "powershell"
                    }
                else:
                    return {"success": False, "error": f"Print command failed: {result.stderr}"}
                    
        except Exception as e:
            return {"success": False, "error": f"Windows print failed: {e}"}
    
    def _print_linux(self, file_path: Path, printer_name: str) -> Dict[str, Any]:
        """Print document on Linux"""
        try:
            if cups:
                # Use CUPS Python bindings
                conn = cups.Connection()
                job_id = conn.printFile(printer_name, str(file_path), file_path.name, {})
                return {
                    "success": True,
                    "printer": printer_name,
                    "file": str(file_path),
                    "job_id": job_id,
                    "method": "cups"
                }
            else:
                # Fallback to lp command
                result = subprocess.run([
                    "lp", "-d", printer_name, str(file_path)
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "printer": printer_name,
                        "file": str(file_path),
                        "method": "lp",
                        "output": result.stdout
                    }
                else:
                    return {"success": False, "error": f"lp command failed: {result.stderr}"}
                    
        except Exception as e:
            return {"success": False, "error": f"Linux print failed: {e}"}
    
    def get_printer_status(self, printer_name: str) -> Dict[str, Any]:
        """Get status information for a specific printer"""
        try:
            for printer in self.available_printers:
                if printer["name"] == printer_name:
                    return {
                        "found": True,
                        "name": printer_name,
                        "status": printer.get("status", "Unknown"),
                        "is_default": printer.get("is_default", False),
                        "details": printer
                    }
            
            return {"found": False, "error": f"Printer '{printer_name}' not found"}
            
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def test_printer(self, printer_name: Optional[str] = None) -> Dict[str, Any]:
        """Test printer by printing a test page"""
        target_printer = printer_name or self.config.printer_name or self.get_default_printer()
        
        if not target_printer:
            return {"success": False, "error": "No printer available for testing"}
        
        try:
            # Create a simple test document
            test_content = f"""
TEST PAGE
=========

Printer: {target_printer}
Date: {Path().cwd().name}  # Simple timestamp alternative
System: {self.system}

This is a test page to verify printer functionality.
If you can read this, the printer is working correctly.

AI Document Agent - Printer Test
"""
            
            # Save test document
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_content)
                test_file = Path(f.name)
            
            try:
                # Print test document
                result = self.print_document(test_file, target_printer)
                
                # Clean up
                test_file.unlink()
                
                if result["success"]:
                    return {
                        "success": True,
                        "message": f"Test page sent to {target_printer}",
                        "printer": target_printer
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Test print failed: {result['error']}"
                    }
                    
            except Exception as e:
                test_file.unlink()  # Clean up on error
                raise e
                
        except Exception as e:
            logger.error(f"Printer test failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_printers(self) -> Dict[str, Any]:
        """Get formatted list of all available printers"""
        return {
            "count": len(self.available_printers),
            "printers": self.available_printers,
            "default": self.get_default_printer(),
            "system": self.system
        }