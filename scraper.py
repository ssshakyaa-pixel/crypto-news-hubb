import os
import json
import time
import re
import feedparser
import requests

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed"
]

# Shared visual database asset line matching frontend structures
IMAGE_LIBRARY = [
    "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=600&auto=format&fit=crop&q=80"
]

def clean_html(raw_html):
    """Strips messy formatting strings to optimize text presentation."""
    if not raw_html:
        return ""
    clean = re.sub(r'<script.*?>.*?</script>', '', raw_html, flags=re.DOTALL)
    clean = re.sub(r'<script.*?>.*?</script>', '', raw_html, flags=re.DOTALL)
    clean = re.sub(r'<style.*?>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = " ".join(clean.split())
    return clean.strip()

def send_to_telegram_channel(title, briefing, image_url, importance):
    """Pushes a stylized news block directly to your audience channel."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials missing from environment. Skipping broadcast channel.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    # Stylized layout using native Telegram HTML parsing capabilities
    caption = (
        f"<b>⚡️ {title.upper()}</b>\n\n"
        f"<b>Market Intelligence Briefing:</b>\n"
        f"{briefing}\n\n"
        f"<i>📊 Impact Priority Rating: {importance}/10</i>"
    )

    payload = {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": caption[:1000],  # Keeps caption strictly under Telegram limits
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=12)
        if response.status_code == 200:
            print(f"-> Broadcast successfully deployed to Telegram!")
        else:
            print(f"-> Telegram Endpoint Alert: {response.text}")
    except Exception as e:
        print(f"-> Telegram connection connection exception: {e}")

def ask_gemini_ai(title, description):
    """Dispatches raw nodes to the model for clean contextual processing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    prompt = (
        f"Analyze this news event:\n"
        f"Title: {title}\n"
        f"Context: {description[:300]}\n\n"
        f"Write a sharp 2-3 sentence market briefing analyzing this news for asset traders.\n"
        f"Do not use markdown formatting. Reply explicitly using this template structure:\n"
        f"SCORE: 7\n"
        f"SUMMARY: One sentence layout line.\n"
        f"BRIEFING: Your multi-sentence market analysis briefing text goes here."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        result = response.json()
        
        if "candidates" in result:
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            importance = 5
            summary = title
            briefing = description

            for line in raw_text.split('\n'):
                if "SCORE:" in line.upper():
                    try: importance = int(re.findall(r'\d+', line)[0])
                    except: pass
                elif "SUMMARY:" in line.upper():
                    summary = line.split(":", 1)[1].strip()
                elif "BRIEFING:" in line.upper():
                    briefing = line.split(":", 1)[1].strip()

            return {"importance": importance, "summary": summary, "briefing": briefing}
    except: pass
    return None

def run_scraper():
    print("Initializing Core Terminal Feed Scraper...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = clean_html(entry.get("title", ""))
                description = clean_html(entry.get("summary", ""))
                link = entry.get("link", "")
                published = entry.get("published", "Recent Sync")

                print(f"Analyzing element: {title[:35]}...")
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis:
                    importance = ai_analysis["importance"]
                    summary = ai_analysis["summary"]
                    briefing = ai_analysis["briefing"]
                else:
                    importance = 5
                    summary = title
                    briefing = description

                all_stories.append({
                    "title": title,
                    "link": link,
                    "time": published,
                    "importance": importance,
                    "summary": summary,
                    "briefing": briefing
                })
                time.sleep(1)
        except Exception as e:
            print(f"Skipping stream conflict: {e}")

    if not all_stories:
        return

    # Sort stories by highest analytical weight score first
    all_stories = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:15]

    # Save database updates cleanly for the frontend terminal framework
    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)

    # Broadcast ONLY the highest-impact trending story to your Telegram channel during this cycle
    top_story = all_stories[0]
    # Filter boundary: Ensure it's important enough to broadcast alert notifications
    if top_story["importance"] >= 6:
        print(f"\nDeploying top market asset to Telegram broadcast feed...")
        assigned_img = IMAGE_LIBRARY[0] # Matches visual indices
        send_to_telegram_channel(
            title=top_story["title"],
            briefing=top_story["briefing"],
            image_url=assigned_img,
            importance=top_story["importance"]
        )

if __name__ == "__main__":
    run_scraper()
