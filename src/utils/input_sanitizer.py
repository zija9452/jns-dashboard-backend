import html
import re
from typing import Union, List, Dict, Any
import bleach

def sanitize_input(input_data: Union[str, List, Dict]) -> Union[str, List, Dict]:
    """
    Sanitize input data to prevent XSS and other injection attacks
    """
    if isinstance(input_data, str):
        # Remove potentially dangerous HTML tags and attributes
        sanitized = bleach.clean(
            input_data,
            tags=['p', 'b', 'i', 'em', 'strong', 'br'],
            attributes={},
            strip=True
        )
        # Escape any remaining HTML
        sanitized = html.escape(sanitized)
        return sanitized
    elif isinstance(input_data, list):
        return [sanitize_input(item) for item in input_data]
    elif isinstance(input_data, dict):
        sanitized_dict = {}
        for key, value in input_data.items():
            # Sanitize both keys and values
            sanitized_key = sanitize_input(key) if isinstance(key, str) else key
            sanitized_dict[sanitized_key] = sanitize_input(value)
        return sanitized_dict
    else:
        # For non-string types, return as is
        return input_data

def validate_email(email: str) -> bool:
    """
    Validate email format
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """
    Validate phone number format
    """
    # Allow various phone number formats
    pattern = r'^[\+]?[1-9][\d]{0,15}$|^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'
    return re.match(pattern, re.sub(r'[^\+\d\(\)\-\s\.]', '', phone)) is not None

def validate_url(url: str) -> bool:
    """
    Validate URL format
    """
    pattern = r'^https?:\/\/(?:[-\w.])+(?:\:[0-9]+)?(?:\/(?:[\w\/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return re.match(pattern, url) is not None

def validate_json(json_str: str) -> bool:
    """
    Validate if string is valid JSON
    """
    try:
        import json
        json.loads(json_str)
        return True
    except ValueError:
        return False

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal
    """
    # Remove any path separators to prevent directory traversal
    filename = re.sub(r'[\/\\]+', '', filename)
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    return filename

def is_safe_string(input_str: str, allowed_chars: str = r'a-zA-Z0-9\s\-_\.') -> bool:
    """
    Check if string contains only safe characters
    """
    pattern = f'^[{allowed_chars}]+$'
    return re.match(pattern, input_str) is not None

class InputValidator:
    """
    Class to encapsulate input validation and sanitization methods
    """

    @staticmethod
    def validate_and_sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize user input for common fields
        """
        sanitized_data = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Sanitize string values
                sanitized_value = sanitize_input(value)

                # Apply specific validation based on field name
                if key.lower() in ['email', 'e_mail', 'mail']:
                    if not validate_email(sanitized_value):
                        raise ValueError(f"Invalid email format for field '{key}'")
                elif key.lower() in ['phone', 'telephone', 'mobile']:
                    if not validate_phone(sanitized_value):
                        raise ValueError(f"Invalid phone number format for field '{key}'")
                elif key.lower() in ['url', 'website', 'link']:
                    if not validate_url(sanitized_value):
                        raise ValueError(f"Invalid URL format for field '{key}'")

                sanitized_data[key] = sanitized_value
            else:
                sanitized_data[key] = value

        return sanitized_data

    @staticmethod
    def validate_pagination_params(skip: int, limit: int, max_limit: int = 100) -> tuple:
        """
        Validate pagination parameters
        """
        if skip < 0:
            raise ValueError("Skip parameter must be non-negative")

        if limit <= 0:
            raise ValueError("Limit parameter must be positive")

        if limit > max_limit:
            raise ValueError(f"Limit parameter exceeds maximum allowed value of {max_limit}")

        return skip, limit