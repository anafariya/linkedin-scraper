# scraper/linkedin_sync_scraper.py
from playwright.sync_api import sync_playwright
import time
import logging
import os
import random
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LinkedInSyncScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        self.playwright = None
        
    def initialize(self):
        """Initialize the browser"""
        logger.info("Initializing browser")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        # Add stealth detection evasion
        self._add_evasion_measures()
        self.page = self.context.new_page()
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        return True
    
    def _add_evasion_measures(self):
        """Add script to evade bot detection"""
        # Disable webdriver property
        self.context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        """)
        
        # Add extra properties to disguise automation
        self.context.add_init_script("""
        window.chrome = {
            runtime: {},
        };
        """)
        
    def _take_screenshot(self, name):
        """Take a screenshot for debugging"""
        if not self.headless:  # Only take screenshots in headless mode
            return
        self.page.screenshot(path=f"screenshots/{name}_{int(time.time())}.png")
    
    def login(self, email, password):
        """Login to LinkedIn with provided credentials"""
        try:
            logger.info(f"Attempting login for {email}")
            self.page.goto("https://www.linkedin.com/login", wait_until="networkidle")
            self._take_screenshot("login_page")
            
            # Enter email
            self.page.fill('input#username', email)
            time.sleep(1)
            
            # Enter password
            self.page.fill('input#password', password)
            time.sleep(1)
            
            # Click login button
            self.page.click('button[type="submit"]')
            
            # Wait for navigation to complete
            self.page.wait_for_load_state("networkidle")
            self._take_screenshot("after_login")
            
            # Check if login was successful
            try:
                success_selectors = [
                    'div.feed-identity-module',
                    'div.search-global-typeahead',
                    '[data-test-id="nav-search-typeahead"]',
                    'div.global-nav__me'
                ]
                
                for selector in success_selectors:
                    try:
                        if self.page.query_selector(selector):
                            logger.info(f"Login successful, found selector: {selector}")
                            return True
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Could not find success indicators: {e}")
            
            # Check if we're still on the login page or got redirected to feed
            current_url = self.page.url
            if "feed" in current_url or "mynetwork" in current_url:
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            self._take_screenshot("login_error")
            raise e
    
    def scrape_profile(self, profile_url):
        """Scrape LinkedIn profile data"""
        try:
            logger.info(f"Scraping profile: {profile_url}")
            
            # Ensure the URL is correctly formatted
            if not profile_url.endswith('/'):
                profile_url = profile_url + '/'
                
            # Navigate to profile
            self.page.goto(profile_url, wait_until="networkidle")
            self._take_screenshot("profile_page")
            time.sleep(2)
            
            # Scroll to mimic human behavior
            self._perform_human_behavior()
            
            # Extract profile data
            profile_data = self._extract_profile_data()
            
            # Add the profile URL to the data
            profile_data['profile_url'] = profile_url
            profile_data['profile_id'] = profile_url.split('/in/')[-1].split('/')[0]
            
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping profile: {str(e)}")
            self._take_screenshot("scrape_error")
            raise e
    
    def _perform_human_behavior(self):
        """Perform random scrolls to mimic human behavior"""
        # Random scrolling
        for i in range(3):
            self.page.mouse.wheel(0, 300 + random.randint(0, 300))
            time.sleep(1 + random.random())
    
    def _extract_profile_data(self):
        """Extract detailed profile data"""
        profile_data = {}
        
        # Get name
        try:
            name_element = self.page.query_selector('h1.text-heading-xlarge')
            if name_element:
                profile_data['name'] = name_element.text_content().strip()
        except:
            pass
            
        # Get title
        try:
            title_element = self.page.query_selector('div.text-body-medium')
            if title_element:
                profile_data['title'] = title_element.text_content().strip()
        except:
            pass
        
        # Get location
        try:
            location_element = self.page.query_selector('span.text-body-small')
            if location_element:
                profile_data['location'] = location_element.text_content().strip()
        except:
            pass
            
        # Get about/introduction
        try:
            about_section = self.page.query_selector('section:has(> div > div > div > span:has-text("About"))')
            if about_section:
                about_text = about_section.query_selector('div.display-flex > span[aria-hidden="true"]')
                if about_text:
                    profile_data['introduction'] = about_text.text_content().strip()
        except:
            pass
            
        # Get current company
        try:
            exp_section = self.page.query_selector('section:has(> div > div > div > span:has-text("Experience"))')
            if exp_section:
                first_exp = exp_section.query_selector('li')
                if first_exp:
                    company_elem = first_exp.query_selector('span.t-14.t-normal')
                    title_elem = first_exp.query_selector('span.t-bold')
                    
                    company = company_elem.text_content().strip() if company_elem else ""
                    title = title_elem.text_content().strip() if title_elem else ""
                    
                    profile_data['current_company'] = {
                        'name': company,
                        'title': title
                    }
        except:
            pass
        
        # Get education
        try:
            edu_section = self.page.query_selector('section:has(> div > div > div > span:has-text("Education"))')
            if edu_section:
                edu_items = edu_section.query_selector_all('li')
                education = []
                
                for item in edu_items:
                    try:
                        school_elem = item.query_selector('.t-bold')
                        degree_elem = item.query_selector('span.t-14.t-normal')
                        
                        if school_elem:
                            edu_entry = {
                                'school': school_elem.text_content().strip(),
                                'degree': degree_elem.text_content().strip() if degree_elem else ""
                            }
                            education.append(edu_entry)
                    except:
                        continue
                        
                if education:
                    profile_data['education'] = education
        except:
            pass
            
        # Get skills
        try:
            # First try getting skills from current page
            skills_section = self.page.query_selector('section:has(> div > div > div > span:has-text("Skills"))')
            skills = []
            
            if skills_section:
                skill_items = skills_section.query_selector_all('span.visually-hidden')
                for item in skill_items:
                    try:
                        skill_text = item.text_content().strip()
                        if skill_text and "skill" not in skill_text.lower():
                            skills.append(skill_text)
                    except:
                        continue
            
            # If no skills found, try the skills page
            if not skills:
                skills_url = profile_url + "details/skills/"
                self.page.goto(skills_url, wait_until="networkidle")
                time.sleep(2)
                
                skill_items = self.page.query_selector_all('span.visually-hidden')
                for item in skill_items:
                    try:
                        skill_text = item.text_content().strip()
                        if skill_text and "skill" not in skill_text.lower():
                            skills.append(skill_text)
                    except:
                        continue
                
                # Navigate back to profile
                self.page.goto(profile_url, wait_until="networkidle")
            
            if skills:
                profile_data['skills'] = list(set(skills))  # Remove duplicates
        except:
            pass
            
        return profile_data
    
    def close(self):
        """Close browser and clean up resources"""
        logger.info("Closing browser and cleaning up resources")
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()