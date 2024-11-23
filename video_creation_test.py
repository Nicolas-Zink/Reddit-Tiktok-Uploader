import praw
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *
import os
import textwrap

def create_text_frame(text, output_path, frame_size=(1080, 1920)):
    """Create a frame with text for TikTok/YouTube Shorts (9:16 ratio)"""
    # Create blank image
    img = Image.new('RGB', frame_size, color='black')
    draw = ImageDraw.Draw(img)
    
    # Try to use Arial, fallback to default if not available
    try:
        font = ImageFont.truetype("Arial.ttf", 60)
    except:
        font = ImageFont.load_default()
    
    # Wrap text to fit frame
    margin = 100
    wrapper = textwrap.TextWrapper(width=30)  # Adjust width based on your needs
    word_list = wrapper.wrap(text)
    
    # Calculate text height
    text_height = len(word_list) * font.size
    y_text = (frame_size[1] - text_height) // 2
    
    # Draw each line of text
    for line in word_list:
        # Get line width to center it
        line_width = font.getlength(line)
        x_text = (frame_size[0] - line_width) // 2
        
        # Draw the line
        draw.text((x_text, y_text), line, font=font, fill='white')
        y_text += font.size + 10  # Add some padding between lines
    
    img.save(output_path)

def test_video_creation():
    try:
        print("Starting video creation test...")
        
        # Initialize Reddit client
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        # Get a post
        subreddit = reddit.subreddit("AmItheAsshole")
        post = next(subreddit.hot(limit=1))
        
        print(f"Creating video for post: {post.title[:50]}...")
        
        # Create temporary directory if it doesn't exist
        if not os.path.exists("temp"):
            os.makedirs("temp")
        
        # Create text-to-speech
        print("Creating audio...")
        tts = gTTS(text=post.title, lang='en')
        tts.save("temp/audio.mp3")
        
        # Create frame
        print("Creating video frame...")
        create_text_frame(post.title, "temp/frame.png")
        
        # Create video
        print("Assembling video...")
        audio = AudioFileClip("temp/audio.mp3")
        frame = ImageClip("temp/frame.png").set_duration(audio.duration)
        
        # Combine audio and video
        final_clip = frame.set_audio(audio)
        
        # Write video file
        print("Saving video...")
        final_clip.write_videofile(
            "output_video.mp4",
            fps=24,
            codec='libx264',
            audio_codec='aac'
        )
        
        print("Video creation complete! Check output_video.mp4")
        
        # Cleanup
        audio.close()
        final_clip.close()
        
    except Exception as e:
        print(f"Error during video creation: {e}")

if __name__ == "__main__":
    test_video_creation()