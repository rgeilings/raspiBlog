import os
import base64
import requests
import markdown
import random
import subprocess
import locale
from datetime import datetime
from openai import OpenAI
from PIL import Image

from dotenv import load_dotenv
from pytrends.request import TrendReq

# Laad omgevingsvariabelen uit .env bestand
load_dotenv()

WORDPRESS_USER = os.getenv('WORDPRESS_USER')
WORDPRESS_APP_PASSWORD = os.getenv('WORDPRESS_APP_PASSWORD')
WP_BASE = os.getenv('WP_BASE')
BLOG_FILE = os.getenv('BLOG_FILE', '/app/blog_post.txt')
BLOG_IMG = os.getenv('BLOG_IMG', '/app/temp_image.jpg')
DALLE3_PROMPT = os.getenv('DALLE3_PROMPT', '/app/dall-e_3_prompt.txt')
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def run_scraper_and_generate_blog():
    result = subprocess.run(['python', '/scripts/maakBlogPost.py'], capture_output=True, text=True)
    print(result.stdout)

def search_unsplash_photos(query):
    url = f"https://api.unsplash.com/search/photos?page=1&query={query}&client_id={UNSPLASH_ACCESS_KEY}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Controleer of het verzoek succesvol was
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Unsplash: {e}")
        return None

def get_random_photo_url(query):
    photos_data = search_unsplash_photos(query)
    if photos_data and 'results' in photos_data:
        photos = photos_data['results']
        if photos:
            random_photo = random.choice(photos)  # Kies een willekeurige foto
            return random_photo['urls']['regular']  # Retourneer de URL van de willekeurige foto
    return None

def generate_ai_image(prompt):
    try:
       client = OpenAI(api_key=OPENAI_API_KEY)
       response = client.images.generate(
         model="dall-e-3",
         prompt=prompt,
         size="1792x1024",
         quality="standard",
         n=1,
       )

       image_url = response.data[0].url
       return image_url
    except Exception as e:
        print(f"Error generating AI image: {e}")
        return None

def download_and_resize_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)

        image = Image.open(filename)
        new_image = image.resize((1792,1024), Image.Resampling.BICUBIC)

        new_image.save(filename,'JPEG')

    else:
        print(f"Failed to download the image: {response.status_code}")

def upload_image_to_wordpress(filename):
    auth = base64.b64encode(f"{WORDPRESS_USER}:{WORDPRESS_APP_PASSWORD}".encode()).decode()
    media_url =  f"{WP_BASE}/wp-json/wp/v2/media"

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    with open(filename, 'rb') as file:
        media_response = requests.post(media_url, headers=headers, files={'file': file})
    if media_response.status_code != 201:
        raise Exception(f"Error uploading image: {media_response.status_code}, {media_response.text}")

    media_id = media_response.json()['id']
    return media_id

def post_to_wordpress(title, content, image_url):
    auth = base64.b64encode(f"{WORDPRESS_USER}:{WORDPRESS_APP_PASSWORD}".encode()).decode()
    post_url = f"{WP_BASE}/wp-json/wp/v2/posts"

    try:
        filename= BLOG_IMG 
        download_and_resize_image(image_url, filename)
        print(f"filename:{filename}")
        media_id = upload_image_to_wordpress(filename)
    except Exception as e:
        print(f"Failed to upload image: {e}")
        media_id = None

    post_data = {
        "title": title,
        "content": content,
        "status": "publish",
        "categories": [2],  # Voeg hier de categorie-ID toe
        "tags": [],  # Voeg hier de tag-ID's toe
    }

    if media_id:
        post_data["featured_media"] = media_id

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    post_response = requests.post(post_url, json=post_data, headers=headers)
    if post_response.status_code != 201:
        raise Exception(f"Error creating post: {post_response.status_code}, {post_response.text}")

def generate_title():
    now = datetime.now()
    title = now.strftime("Trending %A %d %B, %Y %H:%M")
    return title

def main():
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    run_scraper_and_generate_blog()
    
    # Lees de inhoud van BLOG_FILE
    with open(BLOG_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Lees de inhoud van DALLE3_PROMPT
    with open(DALLE3_PROMPT, 'r', encoding='utf-8') as dalle_prompt:
        dall_e_prompt = dalle_prompt.read()

    ai_image_prompt =  f"Gebruik de samenvatting van blogpost als inspiratie voor een afbeelding:{dall_e_prompt}" 
    print(f"ai_image_prompt: {ai_image_prompt}")
    image_url = generate_ai_image(ai_image_prompt)
    if image_url:
         print(f"AI gegenereerde foto URL: {image_url}")
    else:
        print("Er is een fout opgetreden bij het genereren van een AI-afbeelding.")    

    title = generate_title()

    # Converteer de gegenereerde Markdown content naar HTML
    html_content = markdown.markdown(content)

    # Plaats de inhoud naar WordPress  
    post_to_wordpress(title, html_content, image_url)

if __name__ == "__main__":
    main()


