import os
import json
import logging
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_tiktok_uploader():
    """Setup TikTok uploader configuration"""
    try:
        # Get the absolute path to TiktokAutoUploader directory
        base_dir = os.path.abspath("TiktokAutoUploader")
        config_path = os.path.join(base_dir, "config.txt")
        
        # Create cookies directory
        cookies_dir = os.path.join(base_dir, "cookies")
        os.makedirs(cookies_dir, exist_ok=True)
        
        # Create initial config data with the exact expected structure
        config_data = {
            "cookies_dir": "cookies",  # Relative path to cookies directory
            "videos_dir": "videos",    # Directory for videos
            "users": {},               # User profiles
            "default_user": "default"  # Default user profile
        }
        
        # Write config file
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=4)
        
        logger.info(f"Created config file at: {config_path}")
        
        # Create necessary directories
        os.makedirs(os.path.join(base_dir, "videos"), exist_ok=True)
        
        # Change to the TiktokAutoUploader directory
        os.chdir(base_dir)
        
        # Run the login command with name parameter
        cmd = ["python", "cli.py", "login", "-n", "default"]
        logger.info(f"Running login command from directory: {os.getcwd()}")
        logger.info(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Login completed successfully")
            logger.info(result.stdout)
        else:
            logger.error(f"Login failed: {result.stderr}")
            
    except Exception as e:
        logger.error(f"Error during setup: {e}")
        logger.error("Try running the command directly:")
        logger.error("cd TiktokAutoUploader && python cli.py login -n default")

def create_uploader_script():
    """Create script for future uploads"""
    upload_script = """
import subprocess
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def upload_video(video_path, title):
    try:
        # Change to TiktokAutoUploader directory
        os.chdir("TiktokAutoUploader")
        
        # Construct upload command
        cmd = ["python", "cli.py", "upload", "-n", "default", "-v", video_path, "-t", title]
        
        # Run upload command
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Upload successful!")
            logger.info(result.stdout)
            return True
        else:
            logger.error(f"Upload failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error during upload: {e}")
        return False
    finally:
        # Change back to original directory
        os.chdir("..")

def main():
    video_path = "output_video.mp4"
    title = "Check out this Reddit story! #reddit #storytelling #nosleep #scary #story"
    upload_video(video_path, title)

if __name__ == "__main__":
    main()
"""
    
    # Write the upload script
    with open("upload_tiktok.py", "w") as f:
        f.write(upload_script)
    
    logger.info("Created upload_tiktok.py script for future uploads")

if __name__ == "__main__":
    # Clean up any existing files
    if os.path.exists("TiktokAutoUploader/config.txt"):
        os.remove("TiktokAutoUploader/config.txt")
    
    # Remove and recreate directories
    import shutil
    if os.path.exists("TiktokAutoUploader/cookies"):
        shutil.rmtree("TiktokAutoUploader/cookies")
    if os.path.exists("TiktokAutoUploader/videos"):
        shutil.rmtree("TiktokAutoUploader/videos")
    
    # Run setup
    setup_tiktok_uploader()
    
    # Create uploader script
    create_uploader_script()