# scraper/selenium_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os
import random
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LinkedInSeleniumScraper:
    def __init__(self):
        self.driver = None
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        
    def initialize(self):
        """Initialize the browser"""
        logger.info("Initializing browser")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--window-size=1280,800")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Disable automation flags
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        
        # Initialize the driver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # Set script to disable webdriver detection
        self.driver.execute_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false,
        });
        """)
        
        return True
    
    def _take_screenshot(self, name):
        """Take a screenshot for debugging"""
        try:
            self.driver.save_screenshot(f"screenshots/{name}_{int(time.time())}.png")
        except:
            pass
    
    def login(self, email, password):
        """Login to LinkedIn with provided credentials"""
        try:
            logger.info(f"Attempting login for {email}")
            self.driver.get("https://www.linkedin.com/login")
            self._take_screenshot("login_page")
            
            # Enter email
            self.driver.find_element(By.ID, "username").send_keys(email)
            time.sleep(1)
            
            # Enter password
            self.driver.find_element(By.ID, "password").send_keys(password)
            time.sleep(1)
            
            # Click login button
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            
            # Wait for navigation to complete
            time.sleep(3)
            self._take_screenshot("after_login")
            
            # Check if login was successful
            success_selectors = [
                "div.feed-identity-module",
                "div.search-global-typeahead",
                "[data-test-id='nav-search-typeahead']",
                "div.global-nav__me"
            ]
            
            for selector in success_selectors:
                try:
                    if len(self.driver.find_elements(By.CSS_SELECTOR, selector)) > 0:
                        logger.info(f"Login successful, found selector: {selector}")
                        return True
                except:
                    continue
            
            # Check if we're still on the login page or got redirected to feed
            current_url = self.driver.current_url
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
            self.driver.get(profile_url)
            self._take_screenshot("profile_page")
            time.sleep(3)
            
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
            self.driver.execute_script(f"window.scrollBy(0, {300 + random.randint(0, 300)});")
            time.sleep(1 + random.random())
    
    def _extract_profile_data(self):
        """Extract detailed profile data"""
        profile_data = {}
        
        # Get name
        try:
            name_element = self.driver.find_element(By.CSS_SELECTOR, 'h1.text-heading-xlarge')
            if name_element:
                profile_data['name'] = name_element.text.strip()
        except:
            pass
            
        # Get title
        try:
            title_element = self.driver.find_element(By.CSS_SELECTOR, 'div.text-body-medium')
            if title_element:
                profile_data['title'] = title_element.text.strip()
        except:
            pass
        
        # Get location
        try:
            location_element = self.driver.find_element(By.CSS_SELECTOR, 'span.text-body-small')
            if location_element:
                profile_data['location'] = location_element.text.strip()
        except:
            pass
            
        # Get about/introduction
        try:
            about_section = self.driver.find_element(By.XPATH, '//section[.//span[contains(text(), "About")]]')
            if about_section:
                about_text = about_section.find_element(By.CSS_SELECTOR, 'div.display-flex > span[aria-hidden="true"]')
                if about_text:
                    profile_data['introduction'] = about_text.text.strip()
        except:
            pass
            
        # Get current company
        try:
            exp_section = self.driver.find_element(By.XPATH, '//section[.//span[contains(text(), "Experience")]]')
            if exp_section:
                first_exp = exp_section.find_element(By.TAG_NAME, 'li')
                if first_exp:
                    company_elem = first_exp.find_element(By.CSS_SELECTOR, 'span.t-14.t-normal')
                    title_elem = first_exp.find_element(By.CSS_SELECTOR, 'span.t-bold')
                    
                    company = company_elem.text.strip() if company_elem else ""
                    title = title_elem.text.strip() if title_elem else ""
                    
                    profile_data['current_company'] = {
                        'name': company,
                        'title': title
                    }
        except:
            pass
        
        # Get education
        try:
            edu_section = self.driver.find_element(By.XPATH, '//section[.//span[contains(text(), "Education")]]')
            if edu_section:
                edu_items = edu_section.find_elements(By.TAG_NAME, 'li')
                education = []
                
                for item in edu_items:
                    try:
                        school_elem = item.find_element(By.CSS_SELECTOR, '.t-bold')
                        degree_elem = item.find_element(By.CSS_SELECTOR, 'span.t-14.t-normal')
                        
                        if school_elem:
                            edu_entry = {
                                'school': school_elem.text.strip(),
                                'degree': degree_elem.text.strip() if degree_elem else ""
                            }
                            education.append(edu_entry)
                    except:
                        continue
                        
                if education:
                    profile_data['education'] = education
        except:
            pass
            
        # Get skills
        skills = []
        try:
            # Try to find the "Show all X skills" button and click it
            show_skills_buttons = self.driver.find_elements(By.XPATH, '//button[contains(text(), "skills")]')
            if show_skills_buttons:
                for button in show_skills_buttons:
                    try:
                        button.click()
                        time.sleep(2)
                        break
                    except:
                        continue
            
            # Now try to extract skills
            skill_elements = self.driver.find_elements(By.CSS_SELECTOR, 'span.t-bold')
            for element in skill_elements:
                try:
                    skill_text = element.text.strip()
                    if skill_text and len(skill_text) > 1 and not any(x in skill_text.lower() for x in ['skills', 'skill', 'see all']):
                        skills.append(skill_text)
                except:
                    continue
                    
            # If we didn't find skills, try another approach
            if not skills:
                # Go to skills page
                skills_url = profile_url + "details/skills/"
                self.driver.get(skills_url)
                time.sleep(3)
                
                skill_elements = self.driver.find_elements(By.CSS_SELECTOR, 'span.visually-hidden')
                for element in skill_elements:
                    try:
                        skill_text = element.text.strip()
                        if skill_text and "skill" not in skill_text.lower():
                            skills.append(skill_text)
                    except:
                        continue
                
                # Navigate back to profile
                self.driver.get(profile_url)
        except:
            pass
            
        if skills:
            profile_data['skills'] = list(set(skills))  # Remove duplicates
            
        return profile_data
    
    def close(self):
        """Close browser and clean up resources"""
        logger.info("Closing browser and cleaning up resources")
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass