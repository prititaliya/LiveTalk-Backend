"""
QR Code Service

Service for generating QR codes for remote session pairing.
"""
import base64
import io
import logging
from typing import Optional
import qrcode
from qrcode.image.pil import PilImage

logger = logging.getLogger(__name__)


class QRCodeService:
    """Service for generating QR codes"""
    
    def __init__(self, default_size: int = 300):
        """
        Initialize QR code service.
        
        Args:
            default_size: Default QR code size in pixels
        """
        self.default_size = default_size
        logger.info(f"QRCodeService initialized with default size: {default_size}px")
    
    def generate_qr_code(self, data: str, size: Optional[int] = None) -> str:
        """
        Generate a QR code as base64-encoded PNG data.
        
        Args:
            data: Data to encode in QR code
            size: QR code size in pixels (defaults to default_size)
            
        Returns:
            Base64-encoded PNG image data (data URI format)
        """
        if not data:
            raise ValueError("QR code data cannot be empty")
        
        size = size or self.default_size
        
        try:
            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            
            # Add data
            qr.add_data(data)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Resize to requested size
            img = img.resize((size, size))
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Encode as base64
            img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
            
            # Return as data URI
            data_uri = f"data:image/png;base64,{img_base64}"
            
            logger.debug(f"Generated QR code for data: {data[:50]}... (size: {size}px)")
            return data_uri
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}", exc_info=True)
            raise ValueError(f"Failed to generate QR code: {str(e)}")

