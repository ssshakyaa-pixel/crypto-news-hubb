import os
import json
import feedparser
import requests
from datetime import datetime

# 1. List of Crypto News RSS Feeds to monitor
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed"
]

def ask_gemini_ai(title, description):
    """Sends the headline to Gemini AI to clean it up and check importance."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing Gemini API Key!")
        return None

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    
    # We instruct the AI exactly how to respond
    prompt = (
        f"You are a crypto news editor. Analyze this headline and description:\n"
        f"Title: {title}\nDescription: {description}\n\n"
        f"Task:\n"
        f"1. Rate the importance of this news from 1 to 10 (10 being market-changing like BTC hitting a new all-time high).\n"
        f"2. Summarize it clearly in exactly 2 sentences.\n"
        f"Respond ONLY in this exact JSON format, nothing else:\n"
        f'{{"importance": 8, "summary": "Your 2-sentence summary here"}}'
    )
    
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        ai_text = result['contents'][0]['parts'][0]['text'].strip()
        # Clean up any markdown code blocks the AI might mistakenly add
        if ai_text.startswith("```"):
            ai_text = ai_text.split("```")[1].replace("json", "").strip()
        return json.loads(ai_text)
    except Exception as e:
        print(f"AI processing failed: {e}")
        return None

def run_scraper():
    print("Starting Crypto Hub News Robot...")
    
    # Load existing news if file exists
    if os.path.exists("news.json"):
        with open("news.json", "r") as f:
            try:
                all_news = json.load(f)
            except:
                all_news = []
    else:
        all_news = []

    # Keep track of existing links to prevent duplicates
    existing_links = {item['link'] for item in all_news}
    new_stories = []

    # Read news feeds
    for url in RSS_FEEDS:
        print(f"Checking feed: {url}")
        feed = feedparser.parse(url)
        
        # Look at the top 5 newest articles from each feed
        for entry in feed.entries[:5]:
            link = entry.get("link")
            if link in existing_links:
                continue # Skip if we already saved this article before
                
            title = entry.get("title", "")
            description = entry.get("summary", "")
            
            print(f"New headline found: {title}")
            print("Asking Gemini AI to evaluate...")
            
            ai_analysis = ask_gemini_ai(title, description)
            
            if ai_analysis and isinstance(ai_analysis, dict):
                # Only keep stories that are moderately to highly important (score 5 or higher)
                if int(ai_analysis.get("importance", 0)) >= 5:
                    story = {
                        "title": title,
                        "link": link,
                        "summary": ai_analysis.get("summary", ""),
                        "importance": ai_analysis.get("importance", 5),
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    new_stories.append(story)
                    existing_links.add(link)

    # Combine new stories with old stories
    all_news = new_stories + all_news
    
    # Limit database to only keep the top 30 most recent stories
    all_news = all_news[:30]

    # Save everything back to news.json
    with open("news.json", "w") as f:
        json.dump(all_news, indent=4, fp=f)
    print(f"Success! Added {len(new_stories)} new important stories.")

if __name__ == "__main__":
    run_scraper()
