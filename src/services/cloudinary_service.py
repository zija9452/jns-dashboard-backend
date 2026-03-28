import cloudinary
import cloudinary.uploader
from typing import Optional
import logging

from ..config.settings import settings

# Configure Cloudinary
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True  # Use HTTPS
)

logger = logging.getLogger(__name__)


class CloudinaryService:
    """
    Service for handling Cloudinary image uploads and management
    """

    @staticmethod
    async def upload_image(
        file_bytes: bytes,
        folder: str = "products",
        public_id: Optional[str] = None
    ) -> str:
        """
        Upload image to Cloudinary and return public URL
        
        Args:
            file_bytes: Image file bytes
            folder: Folder name in Cloudinary (default: "products")
            public_id: Optional custom public ID for the image
            
        Returns:
            Public URL of uploaded image
        """
        try:
            # Upload to Cloudinary
            upload_result = cloudinary.uploader.upload(
                file_bytes,
                folder=f"european-sports/{folder}",
                public_id=public_id,
                resource_type="image",
                transformation=[
                    {"quality": "auto:good"},  # Auto quality optimization
                    {"fetch_format": "auto"}   # Auto format (WebP for supported browsers)
                ]
            )
            
            # Return secure URL
            return upload_result.get("secure_url")
            
        except Exception as e:
            logger.error(f"Cloudinary upload error: {e}")
            raise Exception(f"Failed to upload image: {str(e)}")

    @staticmethod
    async def delete_image(public_id: str) -> bool:
        """
        Delete image from Cloudinary
        
        Args:
            public_id: Public ID of the image to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            result = cloudinary.uploader.destroy(public_id)
            return result.get("result") == "ok"
        except Exception as e:
            logger.error(f"Failed to delete image: {e}")
            return False

    @staticmethod
    def get_public_id_from_url(url: str) -> Optional[str]:
        """
        Extract public ID from Cloudinary URL

        Args:
            url: Cloudinary image URL

        Returns:
            Public ID or None if extraction fails
        """
        try:
            # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/{transformations}/{version}/{folder}/{public_id}.{ext}
            # Example: https://res.cloudinary.com/dizmve1g6/image/upload/f_auto,q_auto/v1774677020/european-sports/products/product_06d1cc5d2370.jpg

            # Find /upload/ and get everything after it
            upload_index = url.find("/upload/")
            if upload_index == -1:
                return None

            # Get path after /upload/
            path = url[upload_index + 8:]  # +8 to skip "/upload/"

            # Split by '/'
            path_parts = path.split("/")

            # Known Cloudinary transformation parameters
            transform_prefixes = ['f_', 'q_', 'w_', 'h_', 'c_', 'g_', 'x_', 'y_', 'r_', 'z_', 'a_', 'e_', 'o_', 'b_', 'fl_', 'd_', 'p_', 't_']
            
            # Filter out:
            # 1. Transformation params (f_auto, q_auto, w_400, etc.)
            # 2. Version (v1234567890)
            # Keep: folder structure and filename
            clean_parts = []
            for part in path_parts:
                # Skip empty parts
                if not part:
                    continue
                    
                # Skip transformation params (contain '=' or start with known transform prefixes)
                # Examples: f_auto,q_auto or w_400 or f_auto/q_auto
                if '=' in part:
                    continue
                
                # Check if part contains only transformation params (comma-separated)
                # Like: f_auto,q_auto or f_auto,q_auto,w_400
                if ',' in part:
                    items = part.split(',')
                    # If all items are transformation params, skip this part
                    if all(any(item.startswith(prefix) for prefix in transform_prefixes) for item in items):
                        continue
                
                # Skip version numbers (e.g., v1774677020)
                if part.startswith('v') and len(part) > 1 and part[1:].isdigit():
                    continue
                
                # Keep everything else (folders and filename)
                clean_parts.append(part)

            # Last part has the filename - remove extension and query params
            if clean_parts:
                last_part = clean_parts[-1]
                # Remove query parameters first
                last_part = last_part.split("?")[0]
                # Remove extension
                clean_parts[-1] = last_part.rsplit(".", 1)[0]

            # Join to get full public_id
            public_id = "/".join(clean_parts)

            return public_id
        except Exception as e:
            logger.error(f"Failed to extract public ID: {e}")
            return None
