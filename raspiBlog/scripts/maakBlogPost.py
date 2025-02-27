from raspiBlogLib import * # Importeer alle functies uit raspiBlogLib
import base64

def generate_ai_image (prompt, output_filename):
    """
    Genereert een afbeelding op basis van de gegeven prompt via een API-aanroep.

    Parameters:
    - prompt (str): De tekstprompt voor de AI.
    - output_filename (str): De naam van het uitvoerbestand waarin de afbeelding wordt opgeslagen.

    Returns:
    - str: Bestandsnaam van de gegenereerde afbeelding als succesvol, anders None.
    """
    # Payload configureren met de opgegeven prompt
    payload = {
        "prompt": prompt,
        "width": 1200,
        "height": 675,
        "steps": 40,
        "cfg_scale": 1.0,
        "distilled_cfg_scale": 3.5,
        "sampler_index": "Euler",
        "scheduler": "Simple",
        "enable_hr": False,
        "override_settings": {
          "sd_model_checkpoint": "flux1-schnell-fp8.safetensors",
          "forge_additional_modules": [
            "/app/webui-forge/webui/models/VAE/ae.safetensors",
            "/app/webui-forge/webui/models/text_encoder/clip_l.safetensors",
            "/app/webui-forge/webui/models/text_encoder/t5xxl_fp8_e4m3fn.safetensors"
          ]
        },
        "freeu_enabled": True,
        "freeu_b1": 1.01,
        "freeu_b2": 1.02,
        "freeu_s1": 0.99,
        "freeu_s2": 0.95,
        "freeu_start_step": 0,
        "freeu_end_step": 1,
        "perturbed_attention_guidance_enabled": True,
        "perturbed_attention_scale": 3,
        "perturbed_attention_attenuation": 0,
        "perturbed_attention_start_step": 0,
        "perturbed_attention_end_step": 1
    }

    try:
        # Stuur de request naar de API
        print(f"FORGE_API_URL:{FORGE_API_URL}")
        response = requests.post(url=f"{FORGE_API_URL}/sdapi/v1/txt2img", json=payload)

        # Controleer of de response succesvol is
        if response.status_code == 200:
            r = response.json()
            images = r.get('images', [])

            if images:
                # Decodeer en sla de afbeelding op als JPG
                with open(output_filename, 'wb') as f:
                    f.write(base64.b64decode(images[0]))
                print(f"Afbeelding succesvol opgeslagen als {output_filename}")
                return output_filename
            else:
                print("Geen afbeeldingen gevonden in de respons.")
        else:
            print(f"Fout bij API-aanroep: {response.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Netwerkfout: {e}")

    return None

def post_to_wordpress(AI_provider, title, content, filename):
    # Selecteer de juiste WordPress-gebruiker en -applicatie-wachtwoord op basis van AI_provider
    if AI_provider == "Qwen":
        WORDPRESS_USER = WPQWEN_USER
        WORDPRESS_APP_PASSWORD = WPQWEN_APP_PASSWORD
    elif AI_provider == "DeepSeek":
        WORDPRESS_USER = WPDEEPSEEK_USER
        WORDPRESS_APP_PASSWORD = WPDEEPSEEK_APP_PASSWORD
    elif AI_provider == "OpenAI":
        WORDPRESS_USER = WPOPENAI_USER
        WORDPRESS_APP_PASSWORD = WPOPENAI_APP_PASSWORD
    else:
        raise ValueError(f"Ongeldige AI_provider: {AI_provider}. Kies uit 'Qwen', 'DeepSeek' of 'OpenAI'.")

    # Maak de authenticatie-string
    auth = base64.b64encode(f"{WORDPRESS_USER}:{WORDPRESS_APP_PASSWORD}".encode()).decode()

    # Post-URL voor de WordPress REST API
    post_url = f"{WP_BASE}/wp-json/wp/v2/posts"

    try:
        media_id = upload_image_to_wordpress(filename)
    except Exception as e:
        print(f"Failed to upload image: {e}")
        media_id = None

    # Post-data voor het artikel
    post_data = {
        "title": title,
        "content": content,
        "status": "publish",
        "categories": [2],  # Voeg hier de categorie-ID toe
        "tags": [],  # Voeg hier de tag-ID's toe
    }

    # Voeg featured_media toe als er een media_id is
    if media_id:
        post_data["featured_media"] = media_id

    # Headers voor de API-aanvraag
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json"
    }

    # Verstuur de POST-aanvraag naar de WordPress-API
    post_response = requests.post(post_url, json=post_data, headers=headers)

    # Controleer of de post succesvol is gemaakt
    if post_response.status_code != 201:
        raise Exception(f"Error creating post: {post_response.status_code}, {post_response.text}")

    print(f"Post successfully created with AI_provider: {AI_provider}")

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
    files_to_delete = [DALLE3_PROMPT, BLOG_FILE, SUMMARIES_FILE, BLOG_IMG]

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

      filename = generate_ai_image(ai_image_prompt, BLOG_IMG)
      print(f"BLOG_IMG:{BLOG_IMG}, filename:{filename}")
      title = generate_title(NieuwsType)
     
      # Converteer de gegenereerde Markdown content naar HTML
      html_content = markdown.markdown(blog_content)

      # Plaats de inhoud naar WordPress
      post_to_wordpress(AI_provider, title, html_content, filename)
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

