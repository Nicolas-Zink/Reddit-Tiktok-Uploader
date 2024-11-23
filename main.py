import asyncio
from playwright.async_api import async_playwright
import praw
from gtts import gTTS
from gtts.tts import gTTSError
from moviepy.editor import VideoFileClip, CompositeVideoClip, AudioFileClip, ImageClip, concatenate_videoclips, ColorClip
from moviepy.editor import vfx
import os
import textwrap
from PIL import Image
import re
import random
import time
import numpy as np
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def split_content_into_chunks(content, chunk_size=8):
    """Split content into chunks, respecting sentence boundaries when possible"""
    sentences = re.split(r'(?<=[.!?])\s+', content)
    chunks = []
    current_chunk = []
    current_line_count = 0
    
    wrapper = textwrap.TextWrapper(width=85)
    
    for sentence in sentences:
        sentence_lines = wrapper.wrap(sentence)
        sentence_line_count = len(sentence_lines)
        
        if current_line_count + sentence_line_count > chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_line_count = 0
        
        current_chunk.append(sentence)
        current_line_count += sentence_line_count
        
        if current_line_count >= chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_line_count = 0
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

async def capture_reddit_post(url: str, output_path: str, chunk_text: str, is_first_chunk: bool = False, post_title: str = "", author: str = "") -> None:
    """Capture a specific chunk of the Reddit post"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1080, 'height': 100},  # Start with small height
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        page = await context.new_page()
        
        html_content = f"""
        <html>
        <head>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                html, body {{
                    background-color: #1a1a1b;
                    color: #d7dadc;
                    font-family: Arial, sans-serif;
                    height: auto;
                    overflow: hidden;
                }}
                body {{
                    display: flex;
                    justify-content: center;
                    padding: 20px;
                }}
                .post-container {{
                    width: 1000px;
                    background-color: #272729;
                    padding: 30px;
                    border-radius: 4px;
                    display: inline-block;
                    height: fit-content;
                }}
                .subreddit {{
                    color: #d7dadc;
                    font-size: 20px;
                    padding-bottom: 15px;
                }}
                .author {{
                    color: #818384;
                    font-size: 18px;
                    padding-bottom: 20px;
                }}
                .title {{
                    font-size: 32px;
                    font-weight: bold;
                    padding-bottom: 25px;
                    line-height: 1.4;
                }}
                .content {{
                    font-size: 24px;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="post-container">
                {'''<div class="subreddit">r/nosleep</div>''' if is_first_chunk else ''}
                {f'''<div class="author">Posted by u/{author}</div>''' if is_first_chunk else ''}
                {f'''<div class="title">{post_title}</div>''' if is_first_chunk else ''}
                <div class="content">{chunk_text}</div>
            </div>
        </body>
        </html>
        """
        
        await page.set_content(html_content)
        
        # Get the exact height of the content
        content_element = await page.query_selector('.post-container')
        if content_element:
            # Get the bounding box
            box = await content_element.bounding_box()
            if box:
                # Set the viewport to match the exact content size
                exact_height = int(box['height'])
                exact_width = int(box['width'])
                await page.set_viewport_size({
                    'width': exact_width + 40,  # Small padding
                    'height': exact_height + 40  # Small padding
                })
                
                # Take screenshot
                await page.screenshot(path=output_path)
        else:
            raise Exception("Could not find post content")
        
        await browser.close()

def patched_resize(im, newsize):
    """
    Custom resize function that handles both PIL Images and numpy arrays
    """
    # If input is numpy array, convert to PIL Image
    if isinstance(im, np.ndarray):
        pil_im = Image.fromarray(im)
    else:
        pil_im = im
        
    # Handle scale factor
    if isinstance(newsize, (float, int)):
        w = int(pil_im.size[0] * newsize)
        h = int(pil_im.size[1] * newsize)
        resized = pil_im.resize((w, h), Image.Resampling.LANCZOS)
    # Handle width parameter
    elif isinstance(newsize, dict) and 'width' in newsize:
        w = int(newsize['width'])
        ratio = w / float(pil_im.size[0])
        h = int(pil_im.size[1] * ratio)
        resized = pil_im.resize((w, h), Image.Resampling.LANCZOS)
    # Handle height parameter
    elif isinstance(newsize, dict) and 'height' in newsize:
        h = int(newsize['height'])
        ratio = h / float(pil_im.size[1])
        w = int(pil_im.size[0] * ratio)
        resized = pil_im.resize((w, h), Image.Resampling.LANCZOS)
    # Handle tuple/list of dimensions
    elif isinstance(newsize, (tuple, list)) and len(newsize) == 2:
        w = int(newsize[0])
        h = int(newsize[1])
        resized = pil_im.resize((w, h), Image.Resampling.LANCZOS)
    else:
        raise ValueError(f"Invalid newsize parameter: {newsize}")
    
    # Convert back to numpy array if input was numpy array
    if isinstance(im, np.ndarray):
        return np.array(resized)
    return resized

# Monkey patch the resize function
import moviepy.video.fx.resize
moviepy.video.fx.resize.resizer = patched_resize

def create_video_clips(chunk_images, audio_clips, background_video_path, output_size=(1080, 1920), speed_factor=1.3):
    """Create video clips with a single continuous background and faster audio"""
    # Calculate total duration after speed adjustment
    total_duration = sum(audio.duration / speed_factor for audio in audio_clips)
    
    # Load the background video
    background = VideoFileClip(background_video_path)
    
    # Get a random start time that allows for the full duration
    max_start = max(0, background.duration - total_duration)
    start_time = random.uniform(0, max_start)
    
    # Extract the segment we need for the entire video
    background_segment = background.subclip(start_time, start_time + total_duration)
    
    # Calculate dimensions for background resize
    target_height = output_size[1]
    height_scale = target_height / background.h
    target_width = int(background.w * height_scale)
    
    # Resize background to fit height while maintaining aspect ratio
    background_segment = background_segment.resize(height=target_height)
    
    clips = []
    current_time = 0
    
    # Create clips for each chunk
    for screenshot_path, audio_clip in zip(chunk_images, audio_clips):
        # Speed up the audio using the correct method
        faster_audio = audio_clip.fx(vfx.speedx, speed_factor)
        
        # Load and prepare the screenshot
        screenshot = (ImageClip(screenshot_path)
                     .set_duration(faster_audio.duration)
                     .resize(width=int(output_size[0] * 0.9))  # Make screenshot slightly smaller than video width
                     .set_position(('center', 'center')))
        
        # Cut the corresponding portion of background video
        chunk_background = background_segment.subclip(current_time, current_time + faster_audio.duration)
        
        # Center the background video
        x_offset = (output_size[0] - target_width) // 2
        chunk_background = chunk_background.set_position((x_offset, 0))
        
        # Create black background
        black_bg = ColorClip(size=output_size, color=(0, 0, 0)).set_duration(faster_audio.duration)
        
        # Combine background and screenshot for this chunk
        chunk_clip = CompositeVideoClip([
            black_bg,           # Black background layer
            chunk_background,   # Video background layer
            screenshot         # Screenshot on top
        ], size=output_size)
        
        # Add sped-up audio
        chunk_clip = chunk_clip.set_audio(faster_audio)
        clips.append(chunk_clip)
        
        current_time += faster_audio.duration
    
    return clips

async def create_tts_with_retry(text, output_path, max_retries=5, initial_delay=1):
    """Create TTS audio with retry logic and exponential backoff"""
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            tts = gTTS(text=text, lang='en')
            tts.save(output_path)
            # Add a small delay after successful request
            time.sleep(1)
            return True
        except gTTSError as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"Rate limited, waiting {delay} seconds before retry...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
                continue
            raise e

async def create_video():
    try:
        print("Starting video creation process...")
        
        reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        
        subreddit = reddit.subreddit("nosleep")
        for post in subreddit.hot(limit=10):
            if not post.stickied:
                break
        
        print(f"Creating video for post: {post.title[:50]}...")
        
        if not os.path.exists("temp"):
            os.makedirs("temp")
        
        print("Splitting content into chunks...")
        content_chunks = split_content_into_chunks(post.selftext)
        
        chunk_images = []
        audio_clips = []
        
        # First, create all chunks and audio
        for i, chunk in enumerate(content_chunks):
            print(f"Processing chunk {i+1}/{len(content_chunks)}...")
            
            # Create image
            chunk_image_path = f"temp/chunk_{i}.png"
            await capture_reddit_post(
                f"https://www.reddit.com{post.permalink}",
                chunk_image_path,
                chunk,
                is_first_chunk=(i == 0),
                post_title=post.title,
                author=post.author.name if post.author else "[deleted]"
            )
            chunk_images.append(chunk_image_path)
            
            # Create audio with retry logic
            chunk_audio_path = f"temp/chunk_{i}.mp3"
            narration_text = post.title + ". " + chunk if i == 0 else chunk
            
            # Try to create TTS with retry logic
            await create_tts_with_retry(narration_text, chunk_audio_path)
            audio_clips.append(AudioFileClip(chunk_audio_path))
            
            # Add a delay between chunks to avoid rate limiting
            time.sleep(2)
        
        print("Creating video with background...")
        clips = create_video_clips(chunk_images, audio_clips, "background.mp4")
        
        print("Assembling final video...")
        final_clip = concatenate_videoclips(clips)
        
        print("Saving video...")
        final_clip.write_videofile(
            "output_video.mp4",
            fps=24,
            codec='libx264',
            audio_codec='aac'
        )
        
        print("Video creation complete! Check output_video.mp4")
        
        # Cleanup
        final_clip.close()
        for clip in clips:
            clip.close()
        for audio in audio_clips:
            audio.close()
        
    except Exception as e:
        print(f"Error during video creation: {e}")
        raise e

if __name__ == "__main__":
    asyncio.run(create_video())