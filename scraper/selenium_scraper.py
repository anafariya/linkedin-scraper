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
from webdriver_manager.chrome import ChromeDriverManager # Not strictly used but present in original
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class LinkedInSeleniumScraper:
    def __init__(self):
        self.driver = None
        self.headless = os.getenv("HEADLESS", "true").lower() == "true"
        
    def initialize(self):
        """Initialize the browser for Docker environment"""
        logger.info("Initializing browser for Docker environment")
        
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        # Docker-specific options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Anti-detection options
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # For Selenium 4.5.0 compatibility
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create screenshots directory
        os.makedirs("screenshots", exist_ok=True)
        
        try:
            # In Docker, Chrome is installed system-wide
            # If using webdriver_manager, it would be:
            # self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.driver = webdriver.Chrome(options=options)
            logger.info("Chrome initialized successfully in Docker environment")
            
            # Set script to disable webdriver detection
            self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            """)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing Chrome: {e}")
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
                return False # If headless or manual interaction failed
                
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
        
        # Initial scroll height (variable last_height is not used later)
        # last_height = self.driver.execute_script("return document.body.scrollHeight")
        
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
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});", button)
                            time.sleep(0.5)
                            # Click button
                            button.click()
                            time.sleep(1) # Wait for content to expand
                        except Exception as click_err:
                            logger.debug(f"Error clicking button ({button_xpath}): {click_err}")
                except Exception as find_err:
                    logger.debug(f"Error finding buttons ({button_xpath}): {find_err}")
        except Exception as e:
            logger.debug(f"Error expanding sections: {e}")
            
    def extract_name(self):
        """Extract full name using multiple robust methods"""
        logger.info("Extracting name from profile")
        
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
        
        for selector in name_selectors:
            try:
                if selector.startswith('//'):
                    elements = self.driver.find_elements(By.XPATH, selector)
                else:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                if elements and len(elements) > 0:
                    full_name = elements[0].text.strip()
                    if full_name: # Ensure name is not empty
                        logger.info(f"Found name with selector {selector}: {full_name}")
                        
                        # Log details about the element for debugging
                        # element_html = self.driver.execute_script(
                        #     "return arguments[0].outerHTML;", 
                        #     elements[0]
                        # )
                        # logger.debug(f"Name element HTML: {element_html[:200]}") # Log first 200 chars
                        
                        name_parts = full_name.split()
                        first_name = name_parts[0] if len(name_parts) > 0 else full_name
                        last_name = ' '.join(name_parts[1:]) if len(name_parts) >= 2 else ""
                        
                        return {
                            "name": full_name,
                            "first_name": first_name,
                            "last_name": last_name
                        }
            except Exception as e:
                logger.debug(f"Error finding name with selector {selector}: {e}")
        
        logger.warning("Failed to extract name with primary selectors")
        
        # Fallback: find any h1 at the top of the page
        try:
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.driver.save_screenshot("screenshots/name_extraction_fallback.png")
            
            main_content = self.driver.find_element(By.TAG_NAME, "main")
            headings = main_content.find_elements(By.TAG_NAME, "h1")
            
            if headings and len(headings) > 0:
                full_name = headings[0].text.strip()
                if full_name:
                    logger.info(f"Found heading (fallback) that might be name: {full_name}")
                    name_parts = full_name.split()
                    first_name = name_parts[0] if len(name_parts) > 0 else full_name
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) >= 2 else ""
                    return {
                        "name": full_name,
                        "first_name": first_name,
                        "last_name": last_name
                    }
        except Exception as e:
            logger.error(f"Error in fallback name extraction: {e}")
        
        return {"name": "", "first_name": "", "last_name": ""}
    
    def extract_headline(self):
        """Extract the professional headline/title"""
        headline_selectors = [
            'div.text-body-medium.break-words', # More specific modern selector
            '.pv-text-details__left-panel .text-body-medium',
            '.ph5 .mt2 .text-body-medium', # Often title is here
            '.pv-top-card-section__headline',
            '.pv-text-details__left-panel h2'
        ]
        
        for selector in headline_selectors:
            headline = self.get_text_safely(selector)
            if headline:
                logger.info(f"Found headline with selector {selector}: {headline}")
                return headline
        
        logger.warning("Headline not found with any selector.")
        return ""
    
    def extract_location(self):
        """Extract location information"""
        location_selectors = [
            'span.text-body-small.inline.t-black--light.break-words', # Modern selector
            '.pv-text-details__left-panel .text-body-small:not(.hoverable-link-text)',
            '.pv-top-card-section__location',
            '.pv-text-details__left-panel span.text-body-small'
        ]
        
        for selector in location_selectors:
            location = self.get_text_safely(selector)
            if location:
                logger.info(f"Found location with selector {selector}: {location}")
                return location
        
        logger.warning("Location not found with any selector.")
        return ""
    
    def extract_about(self):
        """Extract the about/summary section"""
        try:
            # Try section with "About" header, then get its content
            # Modern LinkedIn uses aria-label for sections
            about_section = self.driver.find_element(By.XPATH, "//section[.//h2[contains(text(), 'About')]] | //div[@aria-label='About' or @aria-labelledby='about-section']")
            # Content is often in a div with 'display-flex' and 'inline-show-more-text'
            about_text_element = about_section.find_element(By.XPATH, ".//div[contains(@class, 'inline-show-more-text')]//span[@aria-hidden='true'] | .//div[contains(@class, 'pv-shared-text-with-see-more')]//p")
            about_text = about_text_element.text.strip()
            if about_text:
                logger.info("Found about section using header approach.")
                return about_text
        except NoSuchElementException:
            logger.debug("About section not found with primary header approach.")
        except Exception as e:
            logger.debug(f"Error in primary about extraction: {e}")

        # Fallback selectors
        about_selectors = [
            ".pv-about__summary-text", # Older
            ".display-flex.ph5.pv3 .inline-show-more-text", # Structure
            "//section[contains(@class, 'artdeco-card') and .//span[text()='About']]//div[contains(@class,'inline-show-more-text')]", # Generic card approach
            "//div[contains(@class,'display-flex')]/span[contains(@class,'text-body-medium') and not(ancestor::*[@aria-label='Name' or @aria-label='Headline' or @aria-label='Location'])]" # Very generic, avoid name/headline
        ]
        
        for selector in about_selectors:
            try:
                if selector.startswith("//"):
                    about = self.get_text_safely(selector, By.XPATH)
                else:
                    about = self.get_text_safely(selector)
                
                if about:
                    logger.info(f"Found about with fallback selector {selector}.")
                    return about
            except Exception:
                pass
        
        logger.warning("About section not found with any selector.")
        return ""
    
    def extract_experience(self):
        """Extract work experience information"""
        experiences = []
        try:
            # Find experience section (modern LinkedIn often uses aria-label)
            exp_section_xpaths = [
                "//section[.//h2[contains(text(), 'Experience')]]",
                "//div[@aria-label='Experience' or @aria-labelledby='experience-section']",
                "//section[contains(@id, 'experience-section') or contains(@class, 'experience-section')]"
            ]
            
            exp_section = None
            for xpath in exp_section_xpaths:
                try:
                    exp_section = self.driver.find_element(By.XPATH, xpath)
                    logger.info(f"Found experience section with XPath: {xpath}")
                    break
                except NoSuchElementException:
                    continue
            
            if exp_section:
                # Experience items are often <li> elements or divs with specific classes
                exp_item_xpaths = [
                    ".//li[contains(@class, 'artdeco-list__item')]", # Common list item class
                    ".//div[contains(@class, 'pvs-entity') and .//img]", # Items often have an image (logo)
                    ".//li" # Generic list items if others fail
                ]

                exp_items = []
                for item_xpath in exp_item_xpaths:
                    try:
                        items = exp_section.find_elements(By.XPATH, item_xpath)
                        if items:
                            exp_items = items
                            logger.info(f"Found {len(exp_items)} experience items using: {item_xpath}")
                            break
                    except Exception:
                        continue
                
                for i, item in enumerate(exp_items):
                    if i >= 5:  # Limit to 5 most recent experiences
                        break
                    
                    job = {}
                    try:
                        # Title: Often a span with 't-bold' or a specific heading
                        title = item.find_element(By.XPATH, ".//span[contains(@class, 't-bold')]/span[@aria-hidden='true'] | .//h3//span[@aria-hidden='true'] | .//div[contains(@class,'display-flex')]/div/div/div/div/span[@aria-hidden='true']").text.strip()
                        job["title"] = title
                    except NoSuchElementException:
                        job["title"] = ""
                        logger.debug(f"Title not found for experience item {i+1}")

                    try:
                        # Company: Often a span near the title, or with 'pv-entity__secondary-title'
                        company = item.find_element(By.XPATH, ".//span[contains(@class, 'job-card-container__company-name')] | .//span[contains(@class, 't-normal')]/span[@aria-hidden='true'] | .//p[contains(@class,'pv-entity__secondary-title')] | .//div[contains(@class,'display-flex')]/div/div/div/span[@aria-hidden='true']").text.strip()
                        # Filter out date range if it gets picked up as company
                        if job["title"] and company.startswith(job["title"]): # sometimes title is part of company string
                             company = company.replace(job["title"], "").strip()
                        job["company"] = company.split('·')[0].strip() # Handle "Company · Full-time"
                    except NoSuchElementException:
                        job["company"] = ""
                        logger.debug(f"Company not found for experience item {i+1}")

                    try:
                        # Dates: Look for 'date-range' or a span with year patterns
                        dates = item.find_element(By.XPATH, ".//span[contains(@class, 'date-range')]/span[@aria-hidden='true'] | .//span[contains(@class, 't-normal t-black--light')]/span[@aria-hidden='true']").text.strip()
                        job["dates"] = dates.split('·')[0].strip() # Handle "Dates · Duration"
                    except NoSuchElementException:
                        job["dates"] = ""
                        logger.debug(f"Dates not found for experience item {i+1}")
                    
                    if job.get("title") or job.get("company"):
                        experiences.append(job)
                        logger.info(f"Extracted experience: {job}")
                    else:
                        logger.debug(f"Skipping empty experience item {i+1}: {item.text[:100]}")

            else:
                logger.warning("Experience section not found.")
        except Exception as e:
            logger.error(f"Error extracting experiences: {e}")
        
        return experiences
    
    def extract_education(self):
        """Extract education information"""
        education_entries = []
        try:
            # Find education section
            edu_section_xpaths = [
                "//section[.//h2[contains(text(), 'Education')]]",
                "//div[@aria-label='Education' or @aria-labelledby='education-section']",
                "//section[contains(@id, 'education-section') or contains(@class, 'education-section')]"
            ]
            
            edu_section = None
            for xpath in edu_section_xpaths:
                try:
                    edu_section = self.driver.find_element(By.XPATH, xpath)
                    logger.info(f"Found education section with XPath: {xpath}")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", edu_section)
                    time.sleep(0.5)
                    self.driver.save_screenshot("screenshots/education_section_found.png")
                    break
                except NoSuchElementException:
                    continue

            if edu_section:
                edu_item_xpaths = [
                    ".//li[contains(@class, 'artdeco-list__item') and .//img]", # Common list item with logo
                    ".//div[contains(@class, 'pvs-entity') and .//img]", # Generic entity with logo
                    ".//li" # Fallback to any list item
                ]
                
                edu_items = []
                for item_xpath in edu_item_xpaths:
                    try:
                        items = edu_section.find_elements(By.XPATH, item_xpath)
                        if items:
                            edu_items = items
                            logger.info(f"Found {len(edu_items)} education items using: {item_xpath}")
                            break
                    except Exception:
                        continue

                for i, item in enumerate(edu_items):
                    entry = {}
                    try:
                        # School Name: Often a bold span or primary text
                        school = item.find_element(By.XPATH, ".//span[contains(@class, 't-bold')]/span[@aria-hidden='true'] | .//div[contains(@class,'display-flex')]/div/div/div/div/span[@aria-hidden='true'] | .//a//div[contains(@class,'align-items-center')]//span[@aria-hidden='true']").text.strip()
                        entry["school"] = school
                    except NoSuchElementException:
                        entry["school"] = ""
                        logger.debug(f"School name not found for education item {i+1}")

                    try:
                        # Degree: Often a span with 't-normal' or secondary text
                        degree_text = item.find_element(By.XPATH, ".//span[contains(@class, 't-normal') and not(contains(@class,'t-black--light'))]/span[@aria-hidden='true'] | .//div[contains(@class,'display-flex')]/div/div/div/span[@aria-hidden='true'][2]").text.strip()
                        if entry.get("school") and degree_text.startswith(entry["school"]):
                            degree_text = degree_text.replace(entry["school"], "").strip()
                        entry["degree"] = degree_text
                    except NoSuchElementException:
                        entry["degree"] = ""
                        logger.debug(f"Degree not found for education item {i+1}")
                    
                    try:
                        # Dates: Look for spans with year patterns or 'date-range'
                        dates = item.find_element(By.XPATH, ".//span[contains(@class, 't-normal t-black--light')]/span[@aria-hidden='true'] | .//span[contains(@class, 'date-range')]/span[@aria-hidden='true']").text.strip()
                        entry["dates"] = dates
                    except NoSuchElementException:
                        entry["dates"] = ""
                        logger.debug(f"Dates not found for education item {i+1}")

                    if entry.get("school"):
                        education_entries.append(entry)
                        logger.info(f"Extracted education: {entry}")
                    else:
                        logger.debug(f"Skipping empty education item {i+1}: {item.text[:100]}")
            else:
                logger.warning("Education section not found.")
        except Exception as e:
            logger.error(f"Error extracting education: {e}")
        
        return education_entries

    def extract_skills(self):
        """Extract skills information"""
        skills = []
        try:
            # Expand skills section (if a "Show all X skills" button exists)
            try:
                show_all_skills_button = self.driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Show all skills')] | //a[contains(@href, 'skills') and .//span[contains(text(),'Show all')]]")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_all_skills_button)
                time.sleep(0.5)
                show_all_skills_button.click()
                time.sleep(2) # Wait for modal or section to expand
                logger.info("Clicked 'Show all skills' button.")
                self.driver.save_screenshot("screenshots/skills_expanded.png")
            except NoSuchElementException:
                logger.info("'Show all skills' button not found or not clickable, proceeding with visible skills.")
            except Exception as e:
                logger.debug(f"Error clicking 'Show all skills': {e}")

            # Skills can be in a modal or directly on the page
            skill_container_xpaths = [
                "//div[contains(@class, 'artdeco-modal__content')]//ul", # Skills in a modal
                "//section[.//h2[contains(text(), 'Skills')]]//ul", # Skills in a section list
                "//div[@aria-label='Skills' or @aria-labelledby='skills-section']//ul",
                "//div[contains(@class, 'pv-skill-categories-section')]", # Older structure
                "//div[contains(@class, 'pvs-list')]" # More generic list container if skills are loose
            ]
            
            skill_elements = []
            for xpath in skill_container_xpaths:
                try:
                    # Look for skill text elements within these containers
                    elements = self.driver.find_elements(By.XPATH, f"{xpath}//span[contains(@class, 't-bold')]/span[@aria-hidden='true'] | {xpath}//div[contains(@class,'pv-skill-category-entity__name-text')] | {xpath}//span[contains(@class, 'pvs-entity__primary-text')]")
                    if elements:
                        skill_elements.extend(elements)
                        logger.info(f"Found {len(elements)} skill elements with XPath segment: {xpath}")
                except NoSuchElementException:
                    continue
            
            if not skill_elements: # Fallback if above specific selectors fail
                 skill_elements = self.driver.find_elements(By.XPATH, "//span[contains(@class, 'pv-skill-category-entity__name-text')] | //span[contains(@class, 'pvs-entity__primary-text')]")


            for element in skill_elements:
                try:
                    skill_text = element.text.strip()
                    if skill_text and skill_text not in skills:
                        skills.append(skill_text)
                except Exception as e:
                    logger.debug(f"Error extracting single skill text: {e}")
            
            logger.info(f"Extracted skills: {skills}")
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
        
        return list(set(skills)) # Return unique skills
    
    def extract_current_company(self, experiences=None):
        """Extract current company information from experiences or directly"""
        if experiences and len(experiences) > 0:
            first_exp = experiences[0]
            # Check if the first experience is current (e.g., "Present" in dates)
            if 'dates' in first_exp and ('present' in first_exp['dates'].lower() or not '-' in first_exp['dates']): # Heuristic for current
                if 'company' in first_exp and 'title' in first_exp:
                    logger.info(f"Current company from experiences: {first_exp['company']}")
                    return {
                        'name': first_exp['company'],
                        'title': first_exp['title']
                    }
        
        # Fallback to direct extraction if not found or experiences are not reliable
        try:
            # This is highly dependent on current LinkedIn layout
            # Attempt to find the element usually displaying current role at top
            current_role_element = self.driver.find_element(By.XPATH, "//div[contains(@class, 'pv-text-details__left-panel')]//h2 | //div[@class='text-body-medium break-words']")
            # The headline often contains the current role
            headline = self.extract_headline() # Re-use headline extraction
            if headline:
                # This is a heuristic, might need refinement. Assumes "Title at Company" format
                parts = headline.split(' at ')
                if len(parts) == 2:
                    logger.info(f"Current company from headline: Title: {parts[0]}, Company: {parts[1]}")
                    return {'title': parts[0].strip(), 'name': parts[1].strip()}
                elif experiences and experiences[0].get('company'): # Fallback to most recent company if headline parse fails
                     logger.info(f"Current company from most recent experience as fallback: {experiences[0]['company']}")
                     return {'title': experiences[0].get('title', headline), 'name': experiences[0]['company']}


        except NoSuchElementException:
            logger.debug("Current company direct extraction element not found.")
        except Exception as e:
            logger.debug(f"Error extracting current company directly: {e}")
        
        logger.warning("Current company not definitively found.")
        return None
    
    def scrape_profile(self, profile_url):
        """Scrape LinkedIn profile data"""
        try:
            logger.info(f"Scraping profile: {profile_url}")
            
            self.driver.get(profile_url)
            logger.info("Waiting for page to load completely...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "main")) # Wait for main content area
            )
            time.sleep(random.uniform(3, 5)) # Additional dynamic wait
            
            self.driver.save_screenshot("screenshots/initial_page_load.png")
            
            profile_data = {
                'profile_url': profile_url,
                'profile_id': profile_url.split('/in/')[-1].split('/')[0].replace('/', '')
            }
            
            logger.info("Scrolling page to ensure content loads...")
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            total_height = int(self.driver.execute_script("return document.body.scrollHeight"))
            for i in range(1, int(total_height / 500) + 2): # Scroll in 500px chunks
                self.driver.execute_script(f"window.scrollTo(0, {i*500});")
                time.sleep(random.uniform(0.5, 1.0))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);") # Scroll to very bottom
            time.sleep(random.uniform(1,2))
            self.driver.execute_script("window.scrollTo(0, 0);") # Scroll back to top
            time.sleep(1)
            
            self.driver.save_screenshot("screenshots/after_scrolling.png")

            # Expand sections like "Show more" for About, Experience, etc.
            self.expand_sections()
            
            # Extract name
            name_data = self.extract_name()
            profile_data.update(name_data)
            
            # Save full page source for debugging if name extraction is problematic
            if not profile_data.get("name"):
                with open("screenshots/full_page_source_no_name.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
            
            # Extract headline/title
            profile_data['headline'] = self.extract_headline()
            
            # Extract location
            profile_data['location'] = self.extract_location()
            
            # Extract about/bio section
            profile_data['about'] = self.extract_about()
            
            # Extract experience
            experiences = self.extract_experience()
            profile_data['experience'] = experiences
            
            # Extract education
            education = self.extract_education()
            profile_data['education'] = education
            
            # Extract skills
            skills = self.extract_skills()
            profile_data['skills'] = skills
            
            # Extract current company
            current_company = self.extract_current_company(experiences)
            if current_company:
                profile_data['current_company'] = current_company
                
            with open("screenshots/profile_data.json", "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
                
            logger.info(f"Completed scraping profile data: {profile_data.get('name', 'N/A')}")
            return profile_data
            
        except TimeoutException:
            logger.error(f"Timeout while loading profile: {profile_url}")
            self.driver.save_screenshot("screenshots/scrape_timeout_error.png")
            return {"error": "Timeout loading profile", "profile_url": profile_url}
        except Exception as e:
            logger.error(f"Error scraping profile {profile_url}: {str(e)}", exc_info=True)
            self.driver.save_screenshot("screenshots/scrape_general_error.png")
            with open("screenshots/scrape_error_page.html", "w", encoding="utf-8") as f:
                if self.driver:
                    f.write(self.driver.page_source)
            return {"error": str(e), "profile_url": profile_url}
            
    def close(self):
        """Close browser and clean up resources"""
        logger.info("Closing browser and cleaning up resources")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error quitting driver: {e}")
            self.driver = None