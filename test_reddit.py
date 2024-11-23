import praw
import sys
import os
def test_reddit_connection():
    try:
        print("Starting Reddit connection test...")
        
        # Initialize Reddit API client
        print("Initializing Reddit client...")
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        print("Attempting to access subreddit...")
        subreddit = reddit.subreddit("AmItheAsshole")
        
        print("Testing subreddit access...")
        print(f"Subreddit name: {subreddit.display_name}")
        print(f"Subreddit title: {subreddit.title}")
        
        print("\nAttempting to fetch posts...")
        for i, post in enumerate(subreddit.hot(limit=2), 1):
            print(f"\nPost {i}:")
            print(f"Title: {post.title}")
            
    except praw.exceptions.ClientException as e:
        print(f"Client Error: {e}")
        print("This usually means there's an issue with your credentials.")
        
    except praw.exceptions.PRAWException as e:
        print(f"PRAW Error: {e}")
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Error type: {type(e)}")
        print("Python version:", sys.version)

if __name__ == "__main__":
    print("Script starting...")
    test_reddit_connection()
    print("Script finished.")