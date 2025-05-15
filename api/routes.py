# api/routes.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Dict, Any, List
import logging
import os
from scraper.linkedin_scraper import LinkedInScraper
import datetime


router = APIRouter()
logger = logging.getLogger(__name__)

class ScrapeProfileRequest(BaseModel):
    profile_url: HttpUrl
    email: Optional[str] = None
    password: Optional[str] = None
    access_token: Optional[str] = None
    
    @validator('profile_url')
    def validate_linkedin_url(cls, v):
        if 'linkedin.com/in/' not in str(v):
            raise ValueError('URL must be a valid LinkedIn profile URL')
        return v

class ProfileData(BaseModel):
    profile_id: str
    name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    introduction: Optional[str] = None
    current_company: Optional[Dict[str, str]] = None
    education: Optional[List[Dict[str, str]]] = None
    skills: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]] = None

# Cache to store scraped profiles
profile_cache = {}

@router.post("/scrape", response_model=ProfileData)
async def scrape_profile(
    request: ScrapeProfileRequest,
    background_tasks: BackgroundTasks
):
    """
    Scrape a LinkedIn profile using either:
    1. LinkedIn credentials (email & password)
    2. A valid LinkedIn access token
    """
    # Extract profile ID from URL
    profile_url = str(request.profile_url)
    profile_id = profile_url.split('/in/')[-1].split('/')[0]
    
    # Check if profile is in cache (and not too old)
    if profile_id in profile_cache:
        logger.info(f"Returning cached profile for {profile_id}")
        return profile_cache[profile_id]
    
    # For development testing, allow using environment variables if credentials not provided
    email = request.email or os.getenv("LINKEDIN_EMAIL")
    password = request.password or os.getenv("LINKEDIN_PASSWORD")
    
    # Validate authentication method
    if not ((email and password) or request.access_token):
        raise HTTPException(
            status_code=400,
            detail="Either LinkedIn credentials (email & password) or access token must be provided"
        )
    
    try:
        # Initialize scraper
        scraper = LinkedInScraper()
        await scraper.initialize()
        
        # Login with credentials
        if email and password:
            login_success = await scraper.login(email, password)
            if not login_success:
                raise HTTPException(
                    status_code=401,
                    detail="LinkedIn login failed. Check credentials or verify if account is not locked."
                )
        # TODO: Implement login with access token if supported
        
        # Scrape profile
        profile_data = await scraper.scrape_profile(profile_url)
        
        # Create response
        response = ProfileData(
            profile_id=profile_id,
            name=profile_data.get('name'),
            title=profile_data.get('title'),
            location=profile_data.get('location'),
            introduction=profile_data.get('introduction'),
            current_company=profile_data.get('current_company'),
            education=profile_data.get('education'),
            skills=profile_data.get('skills'),
            raw_data=profile_data
        )
        
        # Store in cache
        profile_cache[profile_id] = response
        
        # Close browser in background to not block response
        background_tasks.add_task(scraper.close)
        
        return response
        
    except Exception as e:
        logger.error(f"Error scraping profile {profile_id}: {str(e)}")
        # Close browser if it was initialized
        if 'scraper' in locals() and scraper:
            background_tasks.add_task(scraper.close)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear-cache/{profile_id}")
async def clear_cache(profile_id: str):
    """Clear a specific profile from cache for testing"""
    if profile_id in profile_cache:
        del profile_cache[profile_id]
        return {"message": f"Cache cleared for profile {profile_id}"}
    return {"message": "Profile not in cache"}

@router.post("/clear-all-cache")
async def clear_all_cache():
    """Clear all cached profiles for testing"""
    profile_cache.clear()
    return {"message": "All profile caches cleared"}

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {
        "status": "success",
        "message": "API is working",
        "timestamp": str(datetime.datetime.now())
    }


@router.post("/sync-scrape")
def sync_scrape(
    request: ScrapeProfileRequest
):
    """Synchronous scraper endpoint for better compatibility"""
    from scraper.linkedin_sync_scraper import LinkedInSyncScraper
    
    profile_url = str(request.profile_url)
    
    try:
        # Initialize scraper
        scraper = LinkedInSyncScraper()
        scraper.initialize()
        
        # Get credentials from env
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")
        
        if not email or not password:
            raise Exception("LinkedIn credentials not found. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
        
        # Login with credentials
        login_success = scraper.login(email, password)
        
        if not login_success:
            raise Exception("LinkedIn login failed. Check credentials or security verification.")
        
        # Scrape profile
        profile_data = scraper.scrape_profile(profile_url)
        
        # Close browser
        scraper.close()
        
        return profile_data
        
    except Exception as e:
        import traceback
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        # Try to close browser if it was initialized
        if 'scraper' in locals():
            try:
                scraper.close()
            except:
                pass
                
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/selenium-scrape")
def selenium_scrape(
    request: ScrapeProfileRequest
):
    """Scrape LinkedIn profile using Selenium (compatible with Selenium 4.5.0)"""
    from scraper.selenium_scraper import LinkedInSeleniumScraper
    import os
    import traceback
    import time
    
    profile_url = str(request.profile_url)
    
    try:
        print(f"DEBUG: Starting scrape for {profile_url}")
        
        # Initialize scraper
        scraper = LinkedInSeleniumScraper()
        print(f"DEBUG: Initializing browser...")
        scraper.initialize()
        print(f"DEBUG: Browser initialized successfully")
        
        # Get credentials from env
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")
        
        print(f"DEBUG: Using LinkedIn email: {email[:3]}***{email[-4:] if email and len(email) > 7 else ''}")
        
        if not email or not password:
            print("DEBUG: LinkedIn credentials missing in environment variables")
            raise Exception("LinkedIn credentials not found. Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD in .env")
        
        # Login with credentials
        print(f"DEBUG: Attempting login...")
        login_success = scraper.login(email, password)
        print(f"DEBUG: Login success: {login_success}")
        
        if not login_success:
            raise Exception("LinkedIn login failed. Check credentials or security verification.")
        
        # Give a moment for session to stabilize
        time.sleep(3)
        
        # Scrape profile
        print(f"DEBUG: Scraping profile...")
        profile_data = scraper.scrape_profile(profile_url)
        print(f"DEBUG: Profile data retrieved: {profile_data}")
        
        # Close browser
        scraper.close()
        
        print("DEBUG: Scraping completed successfully")
        return profile_data
        
    except Exception as e:
        error_detail = {
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        
        print(f"DEBUG ERROR: {str(e)}")
        print(traceback.format_exc())
        
        # Try to close browser if it was initialized
        if 'scraper' in locals():
            try:
                scraper.close()
            except:
                pass
                
        raise HTTPException(status_code=500, detail=error_detail)


# Add a simple test endpoint that doesn't require browser automation
@router.get("/test")
def test_endpoint():
    return {
        "status": "LinkedIn scraper API is running",
        "time": str(datetime.datetime.now()),
        "credentials": {
            "email_available": bool(os.getenv("LINKEDIN_EMAIL")),
            "password_available": bool(os.getenv("LINKEDIN_PASSWORD"))
        }
    }