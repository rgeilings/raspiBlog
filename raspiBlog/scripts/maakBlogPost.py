from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib

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
        # Gebruik fallback-afbeelding
        fallback_url = "https://renegeilings.nl/wp-content/uploads/2025/01/temp_image-128.jpg"
        return fallback_url

def download_and_resize_image(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        # Genereer de bestandsnaam met de huidige datum en tijd
        now = datetime.now()
        filename = now.strftime("temp_image_%Y%m%d_%H%M%S.jpg")

        # Sla de originele afbeelding op met de gegenereerde bestandsnaam
        with open(filename, 'wb') as f:
            f.write(response.content)
        print(f"Originele afbeelding opgeslagen als: {filename}")

        # Open en resize de afbeelding
        image = Image.open(filename)
        new_image = image.resize((1792, 1024), Image.Resampling.BICUBIC)

        # Sla de resized afbeelding op als temp_image.jpg
        temp_filename = 'temp_image.jpg'
        new_image.save(temp_filename, 'JPEG')
        print(f"Geresizeerde afbeelding opgeslagen als: {temp_filename}")

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

def generate_title(NieuwsType):
    now = datetime.now()
    if 'LEEG' in NieuwsType:
        title = now.strftime("Nieuws %A %d %B, %Y %H:%M")
    else:
        title = now.strftime(f"{NieuwsType} Nieuws %A %d %B, %Y %H:%M")
    return title

def main(NieuwsType):
    locale.setlocale(locale.LC_TIME, 'nl_NL.UTF-8')
    # Mapping van NieuwsType naar view_names
    view_mapping = {
        "Recent": "rb_v_6_random_recent_articles",
        "Sport": "rb_v_6_random_sport_articles",
        "Entertainment": "rb_v_6_random_entertainment_articles"
    }

    # Controleer of het opgegeven NieuwsType geldig is
    if NieuwsType not in view_mapping:
        print(f"Fout: Ongeldige NieuwsType '{NieuwsType}'. Kies uit: {list(view_mapping.keys())}")
        return

    view_name = view_mapping[NieuwsType]  # Koppel de juiste view aan NieuwsType
    print(f"View geselecteerd op basis van NieuwsType '{NieuwsType}': {view_name}")

    start_datetime = datetime.now()

    script_name = Path(__file__).stem  # Haalt de naam van het script op zonder .py-extensie
    #  Dynamisch runid genereren met NieuwsType in de bestandsnaam
    runid = add_new_row_rb_runs(datetime.now(), 'M', f"{script_name}_{NieuwsType.lower()}")  

    # Bestandsnamen
    files_to_delete = [DALLE3_PROMPT, BLOG_FILE, SUMMARIES_FILE]

    # Verwijder de bestanden
    for file in files_to_delete:
       if os.path.exists(file):
           os.remove(file)
           print(f"{file} is verwijderd.")
       else:
           print(f"{file} bestaat niet.")

    generate_summaries(view_name)
    summaries = read_summaries(SUMMARIES_FILE)
    blog_content, AI_provider = maak_blogPost(summaries)

    # schrijf blog_content naar file voor debuggen
    with open(BLOG_FILE, 'w', encoding='utf-8') as file:
        file.write(blog_content)

    print(f"Blog content is geschreven naar '{BLOG_FILE}'")
    
    #controleer of het bestand niet leeg is
    if os.path.getsize(BLOG_FILE) != 0:
      # Lees de inhoud van DALLE3_PROMPT
      with open(DALLE3_PROMPT, 'r', encoding='utf-8') as dalle_prompt:
          ai_image_prompt = dalle_prompt.read()

      image_url = generate_ai_image(ai_image_prompt)

      if image_url:
           print(f"AI gegenereerde foto URL: {image_url}")
      else:
          print("Er is een fout opgetreden bij het genereren van een AI-afbeelding.")
      
      title = generate_title(NieuwsType)
     
      # Converteer de gegenereerde Markdown content naar HTML
      html_content = markdown.markdown(blog_content)

      # Plaats de inhoud naar WordPress
      post_to_wordpress(title, html_content, image_url)
    else:
      print("BLOG_FILE is leeg")

    update_run_status(runid, AI_provider, 'C')

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Geen parameter meegegeven, Recent Nieuws gekozen.")
        NieuwsType='Recent'
    else:
        NieuwsType = sys.argv[1]

    main(NieuwsType)

