# AI-Generated Dutch Blog

Project to create a blog which, including the generation of articles using AI, runs entirely in Docker containers on a Raspberry Pi. More than 95% of the code used for this purpose is "written" by AI. 

Here is how I approach the generation of articles. All steps are automatically performed by AI:

## Step-by-Step Process

### Step 1: Check Trending Topics
Several times a day, the AI bot starts by searching for the top 6 trending topics from Google Trends in the Netherlands. This keeps me informed about what's happening and what people are talking about.

### Step 2: Scrape Articles
For each trending topic, the AI bot searches for Dutch articles on various news sites. A bit of scraping brings together a lot of interesting pieces.

### Step 3: Summarize Articles
The AI bot creates a short, powerful summary for each article. These summaries are combined into one concise piece that you can quickly read.

### Step 4: Find Images
For the first trending topic, the AI bot looks for a beautiful, free photo. If that doesn't work, the AI bot asks DALL-E 3 to create a cool AI-generated image. This way, there's always something nice to accompany the article.

### Step 5: Create Blogpost
With the summary and the image, the AI bot creates a complete blog post. This piece is then ready for publication.

### Step 6: Publish on renegeilings.nl
The blog post is automatically published on my site, [renegeilings.nl](https://renegeilings.nl), in the category "gegenereerd met AI." This ensures there's something new and interesting on my blog every day.

## Current Challenges

At the moment, the articles are not always accurate, and the AI sometimes misinterprets the context of the trending topics. To fetch recent information, I use web scraping techniques, which I have not yet fully mastered. This can also lead to confusion or incorrect information.

To make the information in my articles more relevant and up-to-date, I am working on refining my scraping techniques. This will allow me to collect recent articles (no older than one day) from various sources and enhance them using Retrieval-Augmented Generation (RAG). This way, I can provide the most up-to-date information on trending topics in the Netherlands.

## How to Run the Project

### Prerequisites

- Docker
- Raspberry Pi

### Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/raspiBlog.git
   cd raspiBlog
   ```
2. **adjust the docker-compose.yaml and  scripts/.env files**
   ```bash
   vi docker-compose.yaml
   cd ./scripts
   vi.env
   ```
3. Configure Wordpres manually via browser
4. Build and Run Docker Containers
   ```bash
   docker-compose up -d --build
   ```
5. Use script postTrendingBlog.sh to generate a blogPost. You can use this script in the crontab
   ```bash
   ./postTrendingBlog.sh
    ```
## License
This project is licensed under the MIT License.

## Acknowledgments

- AI content generation powered by OpenAI
- Image generation powered by DALL-E 3
- Hosted on a Raspberry Pi with Docker

---

Feel free to reach out if you have any questions or feedback. Enjoy exploring the world of AI with me!

---

For more detailed information, visit the specific pages on [renegeilings.nl](https://renegeilings.nl) (in Dutch):  "verzamelen data", "maak blogpost met AI" en "post blogpost"

---

