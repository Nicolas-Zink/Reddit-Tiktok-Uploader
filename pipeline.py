import praw
import os
import json
import time
import logging
from datetime import datetime, timezone
import subprocess
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RedditTikTokPipeline:
    def __init__(self):
        # Reddit API credentials
        self.reddit = praw.Reddit(
            client_id="4VdpyQlsHzbdIwOfEov8XQ",
            client_secret="9QGqGfMuLn2GVsHy2XxkIO9StCVzFA",
            user_agent="python:reddit-video-scraper:v1.0 (by /u/IndependentTime4866)"
        )
        
        # File to store last processed post
        self.last_post_file = "last_processed_post.json"
        
        # Initialize last processed post data
        self.last_processed = self.load_last_processed()
    
    def load_last_processed(self):
        """Load information about the last processed post"""
        try:
            if os.path.exists(self.last_post_file):
                with open(self.last_post_file, 'r') as f:
                    return json.load(f)
            return {
                'post_id': None,
                'timestamp': None
            }
        except Exception as e:
            logger.error(f"Error loading last processed post: {e}")
            return {'post_id': None, 'timestamp': None}
    
    def save_last_processed(self, post_id):
        """Save information about the last processed post"""
        try:
            data = {
                'post_id': post_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            with open(self.last_post_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving last processed post: {e}")
    
    def get_top_post(self):
        """Get the current top post from r/nosleep"""
        try:
            subreddit = self.reddit.subreddit("nosleep")
            for post in subreddit.hot(limit=10):  # Check top 10 to skip pinned posts
                if not post.stickied:
                    return post
            return None
        except Exception as e:
            logger.error(f"Error getting top post: {e}")
            return None
    
    def is_new_post(self, post):
        """Check if this is a new top post we haven't processed yet"""
        if not post:
            return False
        
        last_id = self.last_processed.get('post_id')
        if not last_id:
            return True
            
        return post.id != last_id
    
    def run_video_generator(self):
        """Run the video generation script"""
        try:
            logger.info("Starting video generation...")
            result = subprocess.run(["python", "main.py"], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Video generation completed successfully")
                return True
            else:
                logger.error(f"Video generation failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error running video generator: {e}")
            return False
    
    def run_uploader(self):
        """Run the TikTok uploader script"""
        try:
            logger.info("Starting TikTok upload...")
            result = subprocess.run(["python", "uploader.py"], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Upload completed successfully")
                return True
            else:
                logger.error(f"Upload failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error running uploader: {e}")
            return False
    
    def check_video_exists(self):
        """Check if output video exists and is recent"""
        try:
            if not os.path.exists("output_video.mp4"):
                return False
                
            # Check if video is less than 10 minutes old
            video_time = os.path.getmtime("output_video.mp4")
            current_time = time.time()
            return (current_time - video_time) < 600  # 10 minutes in seconds
            
        except Exception as e:
            logger.error(f"Error checking video: {e}")
            return False
    
    def run_pipeline(self):
        """Run the complete pipeline"""
        try:
            logger.info("Starting pipeline check...")
            
            # Get current top post
            top_post = self.get_top_post()
            if not top_post:
                logger.error("Could not get top post")
                return False
            
            # Check if it's a new post
            if not self.is_new_post(top_post):
                logger.info("No new top post found")
                return True
                
            logger.info(f"New top post found: {top_post.title[:50]}...")
            
            # Run video generator
            if not self.run_video_generator():
                logger.error("Video generation failed")
                return False
            
            # Verify video was created
            if not self.check_video_exists():
                logger.error("Video file not found or is too old")
                return False
            
            # Run uploader
            if not self.run_uploader():
                logger.error("Upload failed")
                return False
            
            # Save successful post
            self.save_last_processed(top_post.id)
            logger.info("Pipeline completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return False

def main():
    pipeline = RedditTikTokPipeline()
    
    while True:
        try:
            pipeline.run_pipeline()
            
            # Wait 30 minutes before checking again
            logger.info("Waiting 30 minutes before next check...")
            time.sleep(1800)  # 30 minutes in seconds
            
        except KeyboardInterrupt:
            logger.info("Pipeline stopped by user")
            break
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

if __name__ == "__main__":
    main()