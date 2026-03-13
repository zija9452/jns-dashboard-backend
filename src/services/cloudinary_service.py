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
            # URL format: https://res.cloudinary.com/{cloud_name}/image/upload/{version}/{public_id}.{ext}
            parts = url.split("/upload/")
            if len(parts) != 2:
                return None
            
            # Remove version and extension
            path = parts[1]
            if "/" in path:
                path = path.split("/", 1)[1]  # Remove version
            
            # Remove extension
            public_id = path.rsplit(".", 1)[0]
            return public_id
        except Exception as e:
            logger.error(f"Failed to extract public ID: {e}")
            return None
