from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.action_chains import ActionChains
import os
import time
import pickle
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TikTokUploader:
    def __init__(self, cookies_file="tiktok_cookies.pkl"):
        self.cookies_file = cookies_file
        self.driver = None
        
    def setup_driver(self):
        """Initialize and configure Firefox driver"""
        firefox_options = Options()
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference('useAutomationExtension', False)
        
        # Uncomment the line below to run in headless mode once everything works
        # firefox_options.add_argument("--headless")
        
        self.driver = webdriver.Firefox(options=firefox_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 60)
        
    def save_cookies(self):
        if self.driver:
            pickle.dump(self.driver.get_cookies(), open(self.cookies_file, "wb"))
            logger.info("Cookies saved successfully")
            
    def load_cookies(self):
        if os.path.exists(self.cookies_file):
            cookies = pickle.load(open(self.cookies_file, "rb"))
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.warning(f"Could not load cookie: {e}")
            logger.info("Cookies loaded successfully")
            return True
        return False
    
    def login(self):
        """Handle TikTok login process"""
        try:
            self.setup_driver()
            self.driver.get("https://www.tiktok.com/login")
            
            logger.info("Waiting for manual login...")
            logger.info("Please complete the login process in the browser.")
            logger.info("Press Enter in this terminal after you've successfully logged in.")
            
            input("Press Enter after you've logged in to TikTok... ")
            
            # Verify login was successful
            self.driver.get("https://www.tiktok.com/upload")
            time.sleep(5)
            
            if "/login" in self.driver.current_url:
                logger.error("Login was not successful. Please try again.")
                return False
                
            # Save cookies for future use
            self.save_cookies()
            logger.info("Login successful! Cookies saved for future use.")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
        finally:
            if self.driver:
                self.driver.quit()
    
    def click_post_button(self):
        """Try multiple methods to click the specific Post button div"""
        try:
            # More specific selectors to target only the Post button
            selectors = [
                "//div[contains(@class, 'TUXButton-label') and text()='Post']",  # Most specific XPath
                "//div[contains(@class, 'TUXButton-label')][normalize-space()='Post']",  # Alternative XPath
                "//button[.//div[contains(@class, 'TUXButton-label') and text()='Post']]",  # Target parent button
                "//div[contains(@class, 'TUXButton-label') and not(contains(text(), 'Discard'))][contains(text(), 'Post')]"  # Explicitly exclude Discard
            ]
            
            for selector in selectors:
                try:
                    time.sleep(2)
                    
                    # Try to find the button
                    post_div = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                        
                    # Log what we found to verify it's the right button
                    logger.info(f"Found post element: {post_div.get_attribute('outerHTML')}")
                    logger.info(f"Button text: {post_div.text}")
                    
                    # Additional verification
                    if "discard" in post_div.text.lower():
                        logger.warning("Found Discard button instead of Post button, skipping...")
                        continue
                    
                    # Ensure element is in view
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", post_div)
                    time.sleep(1)
                    
                    # Try different click methods
                    click_methods = [
                        # Method 1: Regular click with parent button
                        lambda: self.driver.execute_script("""
                            var element = arguments[0];
                            var parent = element;
                            // Find the parent button
                            while (parent && parent.tagName !== 'BUTTON') {
                                parent = parent.parentElement;
                            }
                            if (parent && parent.tagName === 'BUTTON') {
                                parent.click();
                            } else {
                                element.click();
                            }
                        """, post_div),
                        
                        # Method 2: Direct click
                        lambda: post_div.click(),
                        
                        # Method 3: Action chains with offset
                        lambda: ActionChains(self.driver).move_to_element(post_div).move_by_offset(0, 0).click().perform(),
                        
                        # Method 4: Find and click the specific Post button
                        lambda: self.driver.execute_script("""
                            var buttons = document.querySelectorAll('div.TUXButton-label');
                            for (var i = 0; i < buttons.length; i++) {
                                if (buttons[i].textContent.trim() === 'Post') {
                                    buttons[i].click();
                                    return true;
                                }
                            }
                        """)
                    ]
                    
                    for i, click_method in enumerate(click_methods, 1):
                        try:
                            click_method()
                            logger.info(f"Successfully clicked post div using method {i}")
                            
                            # Check if click was successful
                            time.sleep(2)
                            if (self.check_upload_started()):
                                logger.info("Upload started successfully!")
                                return True
                                
                        except Exception as e:
                            logger.debug(f"Click method {i} failed: {e}")
                            continue
                    
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            raise Exception("Could not click post div with any method")
            
        except Exception as e:
            logger.error(f"Failed to click post div: {e}")
            return False
        
    def check_upload_started(self):
        """Check if the upload has started"""
        try:
            # Check for various indicators that the upload started
            indicators = [
                "/feed" in self.driver.current_url,
                "/success" in self.driver.current_url,
                len(self.driver.find_elements(By.XPATH, "//*[contains(text(), 'uploading')]")) > 0,
                len(self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Processing')]")) > 0,
                len(self.driver.find_elements(By.XPATH, "//*[contains(text(), 'progress')]")) > 0
            ]
            return any(indicators)
        except:
            return False
        
    def wait_for_upload_completion(self):
        """Wait for upload to complete"""
        try:
            start_time = time.time()
            while time.time() - start_time < 60:
                try:
                    if "/feed" in self.driver.current_url or "/success" in self.driver.current_url:
                        return True
                    success_elements = self.driver.find_elements(By.XPATH, 
                        "//*[contains(text(), 'uploaded') or contains(text(), 'success')]")
                    if success_elements:
                        return True
                except:
                    pass
                time.sleep(2)
            return False
        except Exception as e:
            logger.error(f"Error waiting for upload completion: {e}")
            return False

    def upload_video(self, video_path: str, description: str, max_retries=3):
        """Upload video with retries and better timing"""
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return False
                
            self.setup_driver()
            
            # Load cookies and go to upload page
            self.driver.get("https://www.tiktok.com")
            if self.load_cookies():
                self.driver.get("https://www.tiktok.com/upload")
                time.sleep(5)
                
                if "/login" in self.driver.current_url:
                    logger.error("Cookies expired. Please login again.")
                    os.remove(self.cookies_file)
                    return False
            else:
                logger.error("No saved cookies found. Please run login first")
                return False
            
            # Upload video file
            file_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='file']"))
            )
            file_input.send_keys(os.path.abspath(video_path))
            logger.info("Video file uploaded, waiting for processing...")
            
            # Initial wait for video to start processing
            time.sleep(15)
            logger.info("Initial processing wait complete...")
            
            # Add description
            caption_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[contenteditable='true']"))
            )
            caption_input.clear()
            caption_input.send_keys(description)
            logger.info("Caption added")
            
            # Long wait for video processing to complete
            logger.info("Waiting 60 seconds for video processing to complete...")
            time.sleep(60)  # Wait full minute for processing
            logger.info("60-second wait completed")
            
            # Scroll to ensure post button is visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Try to click post with retries
            for attempt in range(max_retries):
                logger.info(f"Attempting to click post div (attempt {attempt + 1}/{max_retries})")
                if self.click_post_button():
                    logger.info("Waiting for upload to complete...")
                    if self.wait_for_upload_completion():
                        logger.info("Upload completed successfully!")
                        return True
                    
                time.sleep(5)
            
            logger.error("Failed to post automatically after all retries")
            # Take a screenshot for debugging
            self.driver.save_screenshot("failed_upload.png")
            return False
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            self.driver.save_screenshot("error_upload.png")
            return False
        finally:
            if self.driver:
                time.sleep(3)
                self.driver.quit()

def main():
    uploader = TikTokUploader()
    
    # If first time or cookies expired, do login
    if not os.path.exists("tiktok_cookies.pkl"):
        logger.info("First time setup - starting login process...")
        if not uploader.login():
            logger.error("Login failed. Please try again.")
            return
    
    # Upload video
    video_path = "output_video.mp4"
    description = "Check out this Reddit story! #reddit #storytelling #nosleep #scary #story"
    
    success = uploader.upload_video(video_path, description)
    if not success:
        logger.info("Would you like to try logging in again? (y/n)")
        if input().lower() == 'y':
            if os.path.exists("tiktok_cookies.pkl"):
                os.remove("tiktok_cookies.pkl")
            uploader.login()
            uploader.upload_video(video_path, description)

if __name__ == "__main__":
    main()