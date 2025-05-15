# scraper/utils.py
import logging
import re
import os
import time
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def extract_profile_id(profile_url: str) -> str:
    """Extract the LinkedIn profile ID from a profile URL"""
    try:
        # Try to parse out the profile ID/vanity name
        match = re.search(r'linkedin\.com/in/([^/]+)', profile_url)
        if match:
            return match.group(1)
        
        # Return the whole URL if pattern doesn't match
        return profile_url
    except Exception as e:
        logger.error(f"Error extracting profile ID: {e}")
        return profile_url

def clean_whitespace(text: Optional[str]) -> Optional[str]:
    """Clean excessive whitespace from text"""
    if not text:
        return text
    
    # Replace multiple spaces, newlines, tabs with a single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def normalize_company_name(company: Optional[str]) -> Optional[str]:
    """Normalize company name by removing common suffixes"""
    if not company:
        return company
    
    # Remove common company suffixes
    suffixes = [
        r'\bInc\.?\b',
        r'\bLLC\.?\b',
        r'\bLtd\.?\b',
        r'\bCorp\.?\b',
        r'\bCorporation\b',
        r'\bLimited\b',
        r'\bGmbH\b'
    ]
    
    result = company
    for suffix in suffixes:
        result = re.sub(suffix, '', result, flags=re.IGNORECASE)
    
    return clean_whitespace(result)

def rate_limit_check(cache: Dict[str, Any], key: str, min_interval_seconds: int = 300) -> bool:
    """Check if an operation should be rate limited"""
    current_time = time.time()
    
    # Get the last timestamp for this key
    last_time = cache.get(key, 0)
    
    # Check if enough time has passed
    if current_time - last_time < min_interval_seconds:
        return True  # Rate limited
    
    # Update the timestamp
    cache[key] = current_time
    return False  # Not rate limited

def log_to_file(message: str, level: str = "INFO"):
    """Log a message to a file for debugging"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"scraper_{time.strftime('%Y%m%d')}.log")
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] [{level}] {message}\n")