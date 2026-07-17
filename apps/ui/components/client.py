"""
Client component for Billing Extraction application.
Handles UI interactions and data validation.
"""

from typing import Tuple
import streamlit as st

class BillingClient:
    """Handles client-side operations for the billing extraction UI."""
    
    def __init__(self):
        """Initialize the BillingClient."""
        pass
    
    def validate_uploaded_file(self, uploaded_file) -> Tuple[bool, str]:
        """
        Validate uploaded files for security and size constraints.
        
        Args:
            uploaded_file: The file uploaded by the user
            
        Returns:
            Tuple of (is_valid, message) indicating validation result
        """
        # Check file size (50MB max)
        if uploaded_file.size > 50 * 1024 * 1024:
            return False, "File size exceeds maximum limit (50 MB)"
        
        # Check file type
        allowed_types = ["pdf", "jpg", "jpeg", "png"]
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension not in allowed_types:
            return False, f"File type '{file_extension}' is not supported. Allowed types: {', '.join(allowed_types)}"
        
        return True, "File is valid"