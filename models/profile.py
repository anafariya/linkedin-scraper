# models/profile.py
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any

class Education(BaseModel):
    """Education details from LinkedIn profile"""
    school: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
class Experience(BaseModel):
    """Work experience from LinkedIn profile"""
    company: str
    title: str
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: Optional[bool] = None
    
class Company(BaseModel):
    """Current company details"""
    name: str
    title: str
    
class LinkedInProfile(BaseModel):
    """Complete LinkedIn profile data model"""
    profile_id: str = Field(..., description="LinkedIn profile ID/vanity name")
    name: Optional[str] = Field(None, description="Full name of the person")
    title: Optional[str] = Field(None, description="Professional headline/title")
    location: Optional[str] = Field(None, description="Location information")
    introduction: Optional[str] = Field(None, description="About/introduction section")
    
    current_company: Optional[Company] = Field(None, description="Current company details")
    experiences: Optional[List[Experience]] = Field(None, description="Work experiences")
    education: Optional[List[Education]] = Field(None, description="Education details")
    skills: Optional[List[str]] = Field(None, description="Professional skills")
    
    profile_url: Optional[HttpUrl] = Field(None, description="LinkedIn profile URL")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw scraped data")
    
    class Config:
        schema_extra = {
            "example": {
                "profile_id": "johndoe",
                "name": "John Doe",
                "title": "Senior Software Engineer at Example Corp",
                "location": "San Francisco Bay Area",
                "introduction": "Experienced software engineer with a passion for building scalable applications...",
                "current_company": {
                    "name": "Example Corp",
                    "title": "Senior Software Engineer"
                },
                "education": [
                    {
                        "school": "Stanford University",
                        "degree": "Master of Science, Computer Science"
                    }
                ],
                "skills": ["Python", "React", "DevOps", "Machine Learning"],
                "profile_url": "https://www.linkedin.com/in/johndoe/"
            }
        }