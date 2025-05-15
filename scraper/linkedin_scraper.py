# scraper/linkedin_scraper.py
import os
import time
import logging
import json
import asyncio
import random
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LinkedInScraper:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        
    async def initialize(self):
        """Initialize the browser"""
        logger.info("Initializing browser")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Enable request interception to modify headers
        await self.context.route("**/*", self._handle_route)
        self.page = await self.context.new_page()
        
        # Add stealth detection evasion
        await self._add_evasion_measures()
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        
    async def _handle_route(self, route, request):
        """Handle route to add anti-detection headers"""
        headers = {
            **request.headers,
            "Accept-Language": "en-US,en;q=0.9",
            "sec-ch-ua": '"Chromium";v="91", " Not;A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }
        await route.continue_(headers=headers)
    
    async def _add_evasion_measures(self):
        """Add script to evade bot detection"""
        # Disable webdriver property
        await self.page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        """)
        
        # Add extra properties to disguise automation
        await self.page.add_init_script("""
        window.chrome = {
            runtime: {},
        };
        """)
        
        # Add language and platform details
        await self.page.add_init_script("""
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        Object.defineProperty(navigator, 'platform', {
            get: () => 'Win32',
        });
        """)
    
    async def _take_screenshot(self, name):
        """Take a screenshot for debugging"""
        if not self.headless:  # Only take screenshots in headless mode
            return
        await self.page.screenshot(path=f"screenshots/{name}_{int(time.time())}.png")
        
    async def _random_delay(self, min_seconds=1, max_seconds=3):
        """Random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
        
    async def login(self, email: str, password: str) -> bool:
        """Login to LinkedIn with provided credentials"""
        try:
            logger.info(f"Attempting login for {email}")
            await self.page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            await self._take_screenshot("login_page")
            
            # Enter email
            await self.page.fill('input#username', email)
            await self._random_delay(0.5, 1.5)
            
            # Enter password
            await self.page.fill('input#password', password)
            await self._random_delay(0.5, 1.5)
            
            # Click login button
            await self.page.click('button[type="submit"]')
            
            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle")
            await self._take_screenshot("after_login")
            
            # Check if login was successful by looking for feed or homepage elements
            try:
                # Try different selectors that might indicate successful login
                success_selectors = [
                    'div.feed-identity-module',
                    'div.search-global-typeahead',
                    '[data-test-id="nav-search-typeahead"]',
                    'div.global-nav__me'
                ]
                
                for selector in success_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logger.info(f"Login successful, found selector: {selector}")
                        return True
                    except:
                        continue
            
            except Exception as e:
                logger.warning(f"Could not find success indicators: {e}")
            
            # Check for security verification
            security_indicators = [
                'text=Please verify your account',
                'text=Let\'s do a quick security check',
                'text=Verify',
                'input#input__phone_verification_pin',
                'text=Security Verification',
                'text=verification',
                '[data-id="challenge-picker"]'
            ]
            
            for indicator in security_indicators:
                if await self.page.locator(indicator).count() > 0:
                    await self._take_screenshot("security_verification")
                    logger.warning(f"Security verification required: {indicator}")
                    raise Exception("LinkedIn requires security verification. Cannot proceed automatically.")
            
            # Check for wrong password
            if await self.page.locator('text=password you provided must have been incorrect').count() > 0:
                logger.error("Incorrect password")
                return False
                
            # If we reach here, check the URL to determine if login succeeded
            current_url = self.page.url
            if "feed" in current_url or "mynetwork" in current_url or "checkpoint" in current_url:
                logger.info("Login appears successful based on URL")
                return True
                
            logger.error("Login failed, could not verify success")
            await self._take_screenshot("login_failed")
            return False
            
        except TimeoutError as e:
            logger.error(f"Timeout during login: {str(e)}")
            await self._take_screenshot("login_timeout")
            raise Exception(f"Timeout during login: {str(e)}")
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            await self._take_screenshot("login_error")
            raise e
    
    async def scrape_profile(self, profile_url: str) -> Dict[str, Any]:
        """Scrape LinkedIn profile data"""
        try:
            logger.info(f"Scraping profile: {profile_url}")
            
            # Ensure the URL is correctly formatted
            if not profile_url.endswith('/'):
                profile_url = profile_url + '/'
                
            # Navigate to profile
            await self.page.goto(profile_url, wait_until="networkidle")
            await self._take_screenshot("profile_page")
            await self._random_delay()
            
            # Add random delays and scrolls to mimic human behavior
            await self._perform_human_behavior()
            
            # Extract profile data
            profile_data = await self._extract_profile_data()
            
            # Add the profile URL to the data
            profile_data['profile_url'] = profile_url
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping profile: {str(e)}")
            await self._take_screenshot("scrape_error")
            raise e
            
    async def _perform_human_behavior(self):
        """Perform random scrolls and delays to mimic human behavior"""
        # Random scrolling
        scroll_distances = [300, 600, 900, 1200]
        
        for i in range(4):
            scroll_distance = random.choice(scroll_distances)
            await self.page.mouse.wheel(0, scroll_distance)
            await self._random_delay(1, 2.5)
            
            # Occasionally move mouse to random position
            if random.random() > 0.7:
                x = random.randint(100, 1000)
                y = random.randint(100, 600)
                await self.page.mouse.move(x, y)
    
    async def _extract_text_or_empty(self, selector, default=""):
        """Extract text from a selector or return default value if not found"""
        try:
            element = await self.page.locator(selector).first
            content = await element.text_content()
            return content.strip() if content else default
        except Exception:
            return default
            
    async def _extract_profile_data(self) -> Dict[str, Any]:
        """Extract detailed profile data"""
        logger.info("Extracting profile data")
        profile_data = {}
        
        # Take screenshot of the profile for debugging
        await self._take_screenshot("profile_for_extraction")
        
        # Extract intro section
        try:
            logger.info("Extracting intro section")
            
            # Name - try different selectors as LinkedIn changes them frequently
            name_selectors = [
                'h1.text-heading-xlarge',
                'h1.top-card-layout__title',
                '.pv-top-card-section__name',
                'h1.inline'
            ]
            
            for selector in name_selectors:
                try:
                    name_element = await self.page.locator(selector).first
                    name = await name_element.text_content()
                    if name:
                        profile_data['name'] = name.strip()
                        break
                except:
                    continue
                    
            # Title
            title_selectors = [
                'div.text-body-medium',
                '.pv-top-card-section__headline',
                '.top-card-layout__headline'
            ]
            
            for selector in title_selectors:
                try:
                    title_element = await self.page.locator(selector).first
                    title = await title_element.text_content()
                    if title:
                        profile_data['title'] = title.strip()
                        break
                except:
                    continue
            
            # Location
            location_selectors = [
                'span.text-body-small:has-text(".")',
                '.pv-top-card-section__location',
                '.top-card-layout__location'
            ]
            
            for selector in location_selectors:
                try:
                    location_element = await self.page.locator(selector).first
                    location = await location_element.text_content()
                    if location:
                        profile_data['location'] = location.strip()
                        break
                except:
                    continue
            
            # Introduction/About
            about_section_selectors = [
                '//section[.//span[contains(text(), "About")]]',
                '.pv-about-section',
                '#about-section'
            ]
            
            for selector in about_section_selectors:
                try:
                    about_section = await self.page.locator(selector).first
                    if about_section:
                        # Try different content selectors within the about section
                        content_selectors = [
                            'div.display-flex > span[aria-hidden="true"]',
                            'p',
                            '.pv-about__summary-text'
                        ]
                        
                        for content_selector in content_selectors:
                            try:
                                about_element = await about_section.locator(content_selector).first
                                about_text = await about_element.text_content()
                                if about_text and len(about_text.strip()) > 5:  # Ensure it's not empty
                                    profile_data['introduction'] = about_text.strip()
                                    break
                            except:
                                continue
                        
                        if 'introduction' in profile_data:
                            break
                except:
                    continue
        
        except Exception as e:
            logger.warning(f"Error extracting intro section: {str(e)}")
        
        # Extract experience section
        try:
            logger.info("Extracting experience section")
            
            # Try to find and expand the experience section
            experience_section_selectors = [
                '//section[.//span[contains(text(), "Experience")]]',
                '#experience-section',
                '.pv-experience-section'
            ]
            
            for selector in experience_section_selectors:
                if await self.page.locator(selector).count() > 0:
                    experience_section = await self.page.locator(selector).first
                    
                    # Try to click the "Show all experiences" button if it exists
                    show_more_selectors = [
                        'button:has-text("Show all")',
                        'button:has-text("see all")',
                        'button:has-text("Show more")'
                    ]
                    
                    for show_selector in show_more_selectors:
                        try:
                            show_more_button = await experience_section.locator(show_selector).first
                            if await show_more_button.count() > 0:
                                await show_more_button.click()
                                await self.page.wait_for_load_state("networkidle")
                                await self._random_delay(1, 2)
                                break
                        except:
                            continue
                    
                    # Get experience items
                    experience_items_selectors = [
                        'li.artdeco-list__item',
                        'li.pv-entity__position-group',
                        '.pv-profile-section__list-item'
                    ]
                    
                    experiences = []
                    
                    for items_selector in experience_items_selectors:
                        try:
                            items = await experience_section.locator(items_selector).all()
                            if items and len(items) > 0:
                                # We found experience items
                                for item in items[:5]:  # Process first 5 experiences
                                    try:
                                        exp_data = {}
                                        
                                        # Company name
                                        company_selectors = [
                                            'span.hoverable-link-text',
                                            'h4.pv-entity__company-name',
                                            '.pv-entity__company-summary-info h3',
                                            'span.pv-entity__secondary-title'
                                        ]
                                        
                                        for company_selector in company_selectors:
                                            try:
                                                company_element = await item.locator(company_selector).first
                                                company = await company_element.text_content()
                                                if company:
                                                    exp_data['company'] = company.strip()
                                                    break
                                            except:
                                                continue
                                        
                                        # Job title
                                        title_selectors = [
                                            'span.mr1.t-bold',
                                            'span.t-bold:first-of-type',
                                            'h3.t-16',
                                            '.pv-entity__summary-info-margin-top h3',
                                            '.pv-entity__summary-info h3'
                                        ]
                                        
                                        for title_selector in title_selectors:
                                            try:
                                                title_element = await item.locator(title_selector).first
                                                title = await title_element.text_content()
                                                if title:
                                                    exp_data['title'] = title.strip()
                                                    break
                                            except:
                                                continue
                                        
                                        if exp_data and ('company' in exp_data or 'title' in exp_data):
                                            experiences.append(exp_data)
                                    except Exception as e:
                                        logger.warning(f"Error processing experience item: {e}")
                                        continue
                                
                                break  # Break outer loop if we found and processed items
                        except:
                            continue
                    
                    if experiences:
                        profile_data['experiences'] = experiences
                        
                        # Set current company from the first experience
                        if experiences and len(experiences) > 0:
                            profile_data['current_company'] = {
                                'name': experiences[0].get('company', ''),
                                'title': experiences[0].get('title', '')
                            }
                    
                    break  # Break if we found and processed the experience section
            
        except Exception as e:
            logger.warning(f"Error extracting experience section: {str(e)}")
        
        # Extract education section
        try:
            logger.info("Extracting education section")
            
            # Try to find and expand the education section
            education_section_selectors = [
                '//section[.//span[contains(text(), "Education")]]',
                '#education-section',
                '.pv-education-section'
            ]
            
            for selector in education_section_selectors:
                if await self.page.locator(selector).count() > 0:
                    education_section = await self.page.locator(selector).first
                    
                    # Try to click "Show all education" if it exists
                    show_more_selectors = [
                        'button:has-text("Show all")',
                        'button:has-text("see all")',
                        'button:has-text("Show more")'
                    ]
                    
                    for show_selector in show_more_selectors:
                        try:
                            show_more_button = await education_section.locator(show_selector).first
                            if await show_more_button.count() > 0:
                                await show_more_button.click()
                                await self.page.wait_for_load_state("networkidle")
                                await self._random_delay(1, 2)
                                break
                        except:
                            continue
                    
                    # Get education items
                    education_items_selectors = [
                        'li.artdeco-list__item',
                        'li.pv-profile-section__list-item',
                        'li.pv-education-entity'
                    ]
                    
                    education_list = []
                    
                    for items_selector in education_items_selectors:
                        try:
                            items = await education_section.locator(items_selector).all()
                            if items and len(items) > 0:
                                # We found education items
                                for item in items:
                                    try:
                                        edu_data = {}
                                        
                                        # School name
                                        school_selectors = [
                                            'span.hoverable-link-text',
                                            'h3.pv-entity__school-name',
                                            '.pv-entity__degree-info h3'
                                        ]
                                        
                                        for school_selector in school_selectors:
                                            try:
                                                school_element = await item.locator(school_selector).first
                                                school = await school_element.text_content()
                                                if school:
                                                    edu_data['school'] = school.strip()
                                                    break
                                            except:
                                                continue
                                        
                                        # Degree details
                                        degree_selectors = [
                                            'span.t-14.t-normal',
                                            'p.pv-entity__secondary-title',
                                            '.pv-entity__degree-name span.pv-entity__comma-item',
                                            '.pv-entity__degree-info p.pv-entity__secondary-title span'
                                        ]
                                        
                                        for degree_selector in degree_selectors:
                                            try:
                                                degree_element = await item.locator(degree_selector).first
                                                degree = await degree_element.text_content()
                                                if degree and 'degree' not in degree.lower():
                                                    edu_data['degree'] = degree.strip()
                                                    break
                                            except:
                                                continue
                                        
                                        if edu_data and 'school' in edu_data:
                                            education_list.append(edu_data)
                                    except Exception as e:
                                        logger.warning(f"Error processing education item: {e}")
                                        continue
                                
                                break  # Break outer loop if we found and processed items
                        except:
                            continue
                    
                    if education_list:
                        profile_data['education'] = education_list
                    
                    break  # Break if we found and processed the education section
        
        except Exception as e:
            logger.warning(f"Error extracting education section: {str(e)}")
        
        # Extract skills section by navigating to the skills page
        try:
            logger.info("Extracting skills section")
            
            # Create skills URL from the profile URL
            skills_url = profile_url
            if skills_url.endswith('/'):
                skills_url = skills_url[:-1]  # Remove trailing slash
            skills_url = f"{skills_url}/details/skills/"
            
            # Navigate to skills section
            logger.info(f"Navigating to skills page: {skills_url}")
            await self.page.goto(skills_url, wait_until="networkidle")
            await self._take_screenshot("skills_page")
            await self._random_delay(2, 3)
            
            # Check if we need to click "Show more skills" buttons
            show_more_selectors = [
                'button:has-text("Show more")',
                'button:has-text("See more")'
            ]
            
            # Try to expand all skills by clicking "Show more" buttons
            for selector in show_more_selectors:
                while True:
                    try:
                        show_more = await self.page.locator(selector).first
                        if await show_more.count() > 0 and await show_more.is_visible():
                            await show_more.click()
                            await self._random_delay(1, 2)
                        else:
                            break
                    except:
                        break
            
            # Try different skill item selectors
            skills_list = []
            skill_selectors = [
                'span.visually-hidden', 
                '.pv-skill-category-entity__name-text',
                '.pv-skill-entity__skill-name'
            ]
            
            for selector in skill_selectors:
                try:
                    skill_elements = await self.page.locator(selector).all()
                    
                    if skill_elements and len(skill_elements) > 0:
                        for skill_element in skill_elements:
                            try:
                                skill_text = await skill_element.text_content()
                                if skill_text and not any(word in skill_text.lower() for word in ['skill', 'skill level']):
                                    skills_list.append(skill_text.strip())
                            except:
                                continue
                        
                        if skills_list:  # If we found skills with this selector, stop trying others
                            break
                except:
                    continue
            
            # Remove duplicates and empty strings
            skills_list = list(set([s for s in skills_list if s]))
            
            if skills_list:
                profile_data['skills'] = skills_list
        
        except Exception as e:
            logger.warning(f"Error extracting skills section: {str(e)}")
        
        # Navigate back to the main profile page
        await self.page.goto(profile_url, wait_until="networkidle")
        
        return profile_data
    
    async def close(self):
        """Close browser and clean up resources"""
        logger.info("Closing browser and cleaning up resources")
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()