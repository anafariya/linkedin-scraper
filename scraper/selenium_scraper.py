# scraper/selenium_scraper.py
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
import os
import random
import json
from webdriver_manager.chrome import ChromeDriverManager
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
            options.add_argument("--headless")  # Older version uses --headless not --headless=new
        
        options.add_argument("--window-size=1600,1200")  # Larger window size for better content loading
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")  # Helps avoid detection
        
        # For Selenium 4.5.0 compatibility
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        
        try:
            # Use Service class from selenium 4.5.0
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Set script to disable webdriver detection
            self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            """)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Chrome: {e}")
            # Fall back to direct Chrome initialization if ChromeDriverManager fails
            try:
                self.driver = webdriver.Chrome(options=options)
                return True
            except Exception as inner_e:
                logger.error(f"Fallback initialization also failed: {inner_e}")
                raise e
        
    def login(self, email, password):
        """Login to LinkedIn with provided credentials"""
        try:
            logger.info(f"Attempting login for {email}")
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(3)  # Wait for page to load
            
            # Save screenshot
            self.driver.save_screenshot("screenshots/login_page.png")
            
            # Enter email
            self.driver.find_element(By.ID, "username").send_keys(email)
            time.sleep(2 + random.random())
            
            # Enter password
            self.driver.find_element(By.ID, "password").send_keys(password)
            time.sleep(2 + random.random())
            
            # Click login button
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            time.sleep(5)  # Wait longer for login
            
            # Save screenshot after login attempt
            self.driver.save_screenshot("screenshots/after_login.png")
            
            # Check if we're still on login page (failed login)
            if "/login" in self.driver.current_url:
                logger.error("Still on login page, login failed")
                return False
                
            # Check for security verification
            if "checkpoint" in self.driver.current_url or "security" in self.driver.current_url:
                logger.warning("Security checkpoint detected. Manual interaction needed.")
                # Wait longer for manual interaction if headless=false
                if not self.headless:
                    time.sleep(30)  # Wait 30 seconds for manual verification
                    # Check if we moved past the checkpoint
                    if "checkpoint" not in self.driver.current_url and "security" not in self.driver.current_url:
                        return True
                    else:
                        return False
                return False
                
            # If we got redirected anywhere else, consider it success
            logger.info(f"Login successful, current URL: {self.driver.current_url}")
            return True
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            self.driver.save_screenshot("screenshots/login_error.png")
            return False
    
    def get_text_safely(self, selector, by=By.CSS_SELECTOR):
        """Safely get text from an element or return empty string"""
        try:
            elements = self.driver.find_elements(by, selector)
            if elements and len(elements) > 0:
                return elements[0].text.strip()
            return ""
        except Exception as e:
            logger.debug(f"Error getting text from {selector}: {e}")
            return ""
    
    def scroll_page(self):
        """Scroll down the page to load more content"""
        logger.info("Scrolling page to load dynamic content")
        
        # Initial scroll height
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        # Scroll down incrementally with random pauses
        for i in range(5):  # Scroll in stages
            # Scroll down with some randomness
            scroll_amount = random.randint(400, 800)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(1 + random.random())
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    
    def expand_sections(self):
        """Click show more buttons to expand content"""
        logger.info("Attempting to expand sections")
        try:
            # Try to click various "show more" buttons
            show_more_buttons = [
                "//button[contains(text(), 'Show more')]",
                "//button[contains(text(), 'See more')]",
                "//span[contains(text(), 'Show more')]",
                "//button[contains(@aria-label, 'Expand')]"
            ]
            
            for button_xpath in show_more_buttons:
                try:
                    buttons = self.driver.find_elements(By.XPATH, button_xpath)
                    for button in buttons:
                        try:
                            # Scroll to button
                            self.driver.execute_script("arguments[0].scrollIntoView();", button)
                            time.sleep(0.5)
                            # Click button
                            button.click()
                            time.sleep(1)
                        except Exception as click_err:
                            logger.debug(f"Error clicking button: {click_err}")
                except Exception as find_err:
                    logger.debug(f"Error finding buttons: {find_err}")
        except Exception as e:
            logger.debug(f"Error expanding sections: {e}")
            
    def extract_name(self):
        """Extract full name using multiple robust methods"""
        logger.info("Extracting name from profile")
        
        # Try multiple different selectors that could contain the name
        name_selectors = [
            'h1.text-heading-xlarge',                 # Current LinkedIn format
            'h1.inline.t-24.t-black.t-normal',        # Older LinkedIn format
            'h1.text-heading-large',                  # Another LinkedIn format
            '.pv-top-card-section__name',             # Legacy format
            '.pv-text-details__left-panel h1',        # Another possible location
            '.profile-top-card__name',                # Another variant
            '//h1',                                   # Any h1 element as fallback
            '//div[contains(@class, "profile-top-card")]//h1', # Profile card h1
            '//main//h1',                             # Main content h1
            '//div[contains(@class, "pv-text-details__left-panel")]//h1' # Left panel h1
        ]
        
        # First try CSS selectors
        for selector in name_selectors:
            if selector.startswith('//'):
                # This is an XPath selector
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements and len(elements) > 0:
                        full_name = elements[0].text.strip()
                        logger.info(f"Found name with XPath selector {selector}: {full_name}")
                        
                        # Log details about the element for debugging
                        element_html = self.driver.execute_script(
                            "return arguments[0].outerHTML;", 
                            elements[0]
                        )
                        logger.debug(f"Name element HTML: {element_html}")
                        
                        # Split name into first and last
                        name_parts = full_name.split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = ' '.join(name_parts[1:])
                        else:
                            first_name = full_name
                            last_name = ""
                        
                        return {
                            "name": full_name,
                            "first_name": first_name,
                            "last_name": last_name
                        }
                except Exception as e:
                    logger.debug(f"Error finding name with XPath {selector}: {e}")
            else:
                # This is a CSS selector
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and len(elements) > 0:
                        full_name = elements[0].text.strip()
                        logger.info(f"Found name with CSS selector {selector}: {full_name}")
                        
                        # Log details about the element for debugging
                        element_html = self.driver.execute_script(
                            "return arguments[0].outerHTML;", 
                            elements[0]
                        )
                        logger.debug(f"Name element HTML: {element_html}")
                        
                        # Split name into first and last
                        name_parts = full_name.split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]
                            last_name = ' '.join(name_parts[1:])
                        else:
                            first_name = full_name
                            last_name = ""
                        
                        return {
                            "name": full_name,
                            "first_name": first_name,
                            "last_name": last_name
                        }
                except Exception as e:
                    logger.debug(f"Error finding name with CSS selector {selector}: {e}")
        
        # If we got here, we couldn't find the name with any selector
        logger.warning("Failed to extract name with any selector")
        
        # As a last resort, try to find any heading text at the top of the page
        try:
            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Take a screenshot for debugging
            self.driver.save_screenshot("screenshots/name_extraction_top.png")
            
            # Try to find any text that might be a name at the top
            main_content = self.driver.find_element(By.TAG_NAME, "main")
            headings = main_content.find_elements(By.TAG_NAME, "h1")
            
            if headings and len(headings) > 0:
                full_name = headings[0].text.strip()
                logger.info(f"Found heading that might be name: {full_name}")
                
                # Split name into first and last
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                else:
                    first_name = full_name
                    last_name = ""
                
                return {
                    "name": full_name,
                    "first_name": first_name,
                    "last_name": last_name
                }
        except Exception as e:
            logger.error(f"Error in fallback name extraction: {e}")
        
        # If all attempts failed, return empty data
        return {"name": "", "first_name": "", "last_name": ""}
    
    def extract_headline(self):
        """Extract the professional headline/title"""
        headline_selectors = [
            'div.text-body-medium',
            '.pv-text-details__left-panel .text-body-medium',
            '.ph5 .mt2',
            '.pv-top-card-section__headline',
            '.pv-text-details__left-panel h2'
        ]
        
        for selector in headline_selectors:
            headline = self.get_text_safely(selector)
            if headline:
                return headline
        
        return ""
    
    def extract_location(self):
        """Extract location information"""
        location_selectors = [
            '.pv-text-details__left-panel .text-body-small:not(.hoverable-link-text)',
            'span.text-body-small.inline.t-black--light.break-words',
            '.pv-top-card-section__location',
            '.pv-text-details__left-panel span.text-body-small'
        ]
        
        for selector in location_selectors:
            location = self.get_text_safely(selector)
            if location:
                return location
        
        return ""
    
    def extract_about(self):
        """Extract the about/summary section"""
        # Try multiple approaches to find the about section
        try:
            # Try section with "About" header
            about_section = self.driver.find_element(By.XPATH, "//section[.//div[contains(text(), 'About')]]")
            about_text = about_section.find_element(By.XPATH, ".//div[contains(@class, 'inline-show-more-text')]").text.strip()
            return about_text
        except Exception:
            pass
        
        # Try other selectors
        about_selectors = [
            ".pv-about__summary-text",
            ".pv-about-section div.pv-shared-text-with-see-more",
            ".display-flex.ph5.pv3",
            "//div[contains(@class,'display-flex')]/span[contains(@class,'text-body-medium')]"
        ]
        
        for selector in about_selectors:
            try:
                if selector.startswith("//"):
                    about = self.get_text_safely(selector, By.XPATH)
                else:
                    about = self.get_text_safely(selector)
                
                if about:
                    return about
            except Exception:
                pass
        
        return ""
    
    def extract_experience(self):
        """Extract work experience information"""
        experiences = []
        
        try:
            # Find experience section
            exp_section_xpaths = [
                "//section[.//div[contains(text(), 'Experience')]]",
                "//section[contains(@class, 'experience-section')]",
                "//section[contains(@id, 'experience-section')]"
            ]
            
            exp_section = None
            for xpath in exp_section_xpaths:
                try:
                    exp_section = self.driver.find_element(By.XPATH, xpath)
                    break
                except NoSuchElementException:
                    continue
            
            if exp_section:
                # Try to find experience list items
                exp_items = exp_section.find_elements(By.XPATH, ".//li")
                
                # Process each item
                for i, item in enumerate(exp_items):
                    if i >= 5:  # Limit to 5 most recent experiences
                        break
                    
                    try:
                        job = {}
                        
                        # Try to extract title, company, dates
                        title = ""
                        company = ""
                        dates = ""
                        
                        # Try various selectors for title
                        try:
                            title = item.find_element(By.XPATH, ".//h3 | .//span[contains(@class, 'mr1 t-bold')]").text.strip()
                        except Exception:
                            pass
                            
                        # Try various selectors for company
                        try:
                            company = item.find_element(By.XPATH, ".//p[contains(@class, 'hoverable-link-text')] | .//h4").text.strip()
                        except Exception:
                            pass
                            
                        # Try to extract dates
                        try:
                            dates = item.find_element(By.XPATH, ".//span[contains(@class, 'date-range')] | .//div[contains(@class, 'date-range')]").text.strip()
                        except Exception:
                            pass
                        
                        if title or company:
                            job["title"] = title
                            job["company"] = company
                            job["dates"] = dates
                            experiences.append(job)
                    except Exception as exp_err:
                        logger.debug(f"Error processing experience item: {exp_err}")
        except Exception as e:
            logger.debug(f"Error extracting experiences: {e}")
        
        return experiences
    
    def extract_education(self):
        """Extract education information"""
        education = []
        
        try:
            # Find education section
            edu_section_xpaths = [
                "//section[.//div[contains(text(), 'Education')]]",
                "//section[contains(@class, 'education-section')]",
                "//section[contains(@id, 'education-section')]"
            ]
            
            edu_section = None
            for xpath in edu_section_xpaths:
                try:
                    edu_section = self.driver.find_element(By.XPATH, xpath)
                    break
                except NoSuchElementException:
                    continue
            
            if edu_section:
                # Try to find education list items
                edu_items = edu_section.find_elements(By.XPATH, ".//li")
                
                # Process each item
                for item in edu_items:
                    try:
                        edu_entry = {}
                        
                        # Try to extract school, degree, dates
                        school = ""
                        degree = ""
                        dates = ""
                        
                        # Try various selectors for school
                        try:
                            school = item.find_element(By.XPATH, ".//h3 | .//div[contains(@class, 'pv-entity__school-name')]").text.strip()
                        except Exception:
                            pass
                            
                        # Try various selectors for degree
                        try:
                            degree = item.find_element(By.XPATH, ".//p[contains(@class, 'degree-name')] | .//span[contains(@class, 'pv-entity__secondary-title')]").text.strip()
                        except Exception:
                            pass
                            
                        # Try to extract dates
                        try:
                            dates = item.find_element(By.XPATH, ".//p[contains(@class, 'pv-entity__dates')] | .//span[contains(@class, 'date-range')]").text.strip()
                        except Exception:
                            pass
                        
                        if school:
                            edu_entry["school"] = school
                            edu_entry["degree"] = degree
                            edu_entry["dates"] = dates
                            education.append(edu_entry)
                    except Exception as edu_err:
                        logger.debug(f"Error processing education item: {edu_err}")
        except Exception as e:
            logger.debug(f"Error extracting education: {e}")
        
        return education
    
    def extract_skills(self):
        """Extract skills information"""
        skills = []
        
        try:
            # Try to expand skills section first
            try:
                show_skills_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Show all skills')]")
                self.driver.execute_script("arguments[0].scrollIntoView();", show_skills_button)
                show_skills_button.click()
                time.sleep(2)
            except Exception:
                pass
            
            # Find and extract skills
            skill_section_xpaths = [
                "//section[.//div[contains(text(), 'Skills')]]",
                "//section[contains(@class, 'skills-section')]",
                "//section[contains(@id, 'skills-section')]",
                "//div[contains(@class, 'pv-skill-categories-section')]"
            ]
            
            for xpath in skill_section_xpaths:
                try:
                    # Find the skills section
                    skills_section = self.driver.find_element(By.XPATH, xpath)
                    
                    # Try different selectors for skill items
                    skill_selectors = [
                        ".//span[contains(@class, 'pv-skill-category-entity__name-text')]",
                        ".//span[contains(@class, 'pvs-entity__primary-text')]",
                        ".//li//span[contains(@class, 'text-body-small')]"
                    ]
                    
                    for selector in skill_selectors:
                        try:
                            skill_elements = skills_section.find_elements(By.XPATH, selector)
                            for element in skill_elements:
                                skill_text = element.text.strip()
                                if skill_text and skill_text not in skills:
                                    skills.append(skill_text)
                            
                            # If we found skills, break
                            if skills:
                                break
                        except Exception:
                            continue
                    
                    # If we found skills, break out of section loop
                    if skills:
                        break
                except NoSuchElementException:
                    continue
            
            # If we couldn't find skills via the UI, try to extract from page source
            if not skills:
                # Look for specific skill-related content in page source
                page_source = self.driver.page_source.lower()
                common_skills = [
                    "javascript", "python", "java", "c++", "react", "angular", "node.js", 
                    "aws", "azure", "cloud", "docker", "kubernetes", "devops", "agile", 
                    "product management", "leadership", "project management", "sql", 
                    "mongodb", "database", "machine learning", "data science"
                ]
                
                for skill in common_skills:
                    # Check if the skill is mentioned with skill-related context
                    if f"skill\">{skill}" in page_source or f">{skill}</span" in page_source:
                        if skill not in skills:
                            skills.append(skill)
        except Exception as e:
            logger.debug(f"Error extracting skills: {e}")
        
        return skills
    
    def extract_current_company(self, experiences=None):
        """Extract current company information from experiences or directly"""
        # If experiences were already extracted, use the first one as current
        if experiences and len(experiences) > 0:
            first_exp = experiences[0]
            if 'company' in first_exp and 'title' in first_exp:
                return {
                    'name': first_exp['company'],
                    'title': first_exp['title']
                }
        
        # Otherwise try direct extraction
        try:
            company_elements = self.driver.find_elements(By.XPATH, 
                "//section[.//span[contains(text(), 'Experience')]]//li[1]//span[contains(@class, 'hoverable-link-text')]")
            if company_elements and len(company_elements) > 0:
                current_company = company_elements[0].text.strip()
                
                # Try to get title directly
                title = self.get_text_safely('div.text-body-medium')
                
                return {
                    'name': current_company,
                    'title': title
                }
        except Exception as e:
            logger.debug(f"Error extracting current company directly: {e}")
        
        return None
    
    def scrape_profile(self, profile_url):
        """Scrape LinkedIn profile data with improved name extraction"""
        try:
            logger.info(f"Scraping profile: {profile_url}")
            
            # Navigate to profile
            self.driver.get(profile_url)
            logger.info("Waiting for page to load completely...")
            time.sleep(5)  # Initial wait for page load
            
            # Save screenshot of initial page load
            self.driver.save_screenshot("screenshots/initial_page_load.png")
            
            # Basic profile data dictionary
            profile_data = {
                'profile_url': profile_url,
                'profile_id': profile_url.split('/in/')[-1].split('/')[0].replace('/', '')
            }
            
            # Scroll slowly to ensure all content loads
            logger.info("Scrolling page to ensure content loads...")
            self.driver.execute_script("window.scrollTo(0, 0);")  # First go to top
            time.sleep(1)
            
            # Scroll down in small increments
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            for i in range(10):  # Scroll in 10 increments
                scroll_height = total_height * (i + 1) / 10
                self.driver.execute_script(f"window.scrollTo(0, {scroll_height});")
                time.sleep(0.5)  # Short pause between scrolls
            
            # Go back to top for extraction
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Take screenshot after scrolling
            self.driver.save_screenshot("screenshots/after_scrolling.png")
            
            # Extract name - special focus on this
            logger.info("Extracting name (special focus)...")
            # First make sure we're at the top of the page
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Try to use our enhanced name extraction
            name_data = self.extract_name()
            if name_data["name"]:
                logger.info(f"Successfully extracted name: {name_data['name']}")
                profile_data.update(name_data)
            else:
                logger.warning("Enhanced name extraction failed, trying direct methods...")
                
                # Direct method 1: Try finding h1 elements anywhere
                try:
                    h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
                    if h1_elements and len(h1_elements) > 0:
                        for h1 in h1_elements:
                            text = h1.text.strip()
                            if text:
                                logger.info(f"Found h1 with text: {text}")
                                profile_data['name'] = text
                                
                                # Try to split into first/last name
                                name_parts = text.split()
                                if len(name_parts) >= 2:
                                    profile_data['first_name'] = name_parts[0]
                                    profile_data['last_name'] = ' '.join(name_parts[1:])
                                else:
                                    profile_data['first_name'] = text
                                    profile_data['last_name'] = ""
                                break
                except Exception as h1_err:
                    logger.error(f"Error in direct h1 extraction: {h1_err}")
            
            # Save full page source for debugging
            with open("screenshots/full_page_source.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
                
            # Continue with other extractions
            
            # Extract headline/title
            title = self.extract_headline()
            if title:
                profile_data['title'] = title
            
            # Extract location
            location = self.extract_location()
            if location:
                profile_data['location'] = location
            
            # Extract about/bio section
            about = self.extract_about()
            if about:
                profile_data['introduction'] = about
            
            # Extract experience
            experiences = self.extract_experience()
            if experiences:
                profile_data['experience'] = experiences
            
            # Extract education
            education = self.extract_education()
            if education:
                profile_data['education'] = education
            
            # Extract skills
            skills = self.extract_skills()
            if skills:
                profile_data['skills'] = skills
            
            # Extract current company (either from experiences or directly)
            current_company = self.extract_current_company(experiences)
            if current_company:
                profile_data['current_company'] = current_company
                
            # Save the extracted data for debugging
            with open("screenshots/profile_data.json", "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
                
            logger.info(f"Completed scraping profile data: {json.dumps(profile_data, indent=2)}")
            return profile_data
            
        except Exception as e:
            logger.error(f"Error scraping profile: {str(e)}")
            self.driver.save_screenshot("screenshots/scrape_error.png")
            return {"error": str(e), "profile_url": profile_url, "profile_id": profile_url.split('/in/')[-1].split('/')[0].replace('/', '')}
            
    def close(self):
        """Close browser and clean up resources"""
        logger.info("Closing browser and cleaning up resources")
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass