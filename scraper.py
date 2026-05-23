import os
import json
import time
import re
import random
import feedparser
import requests

# The top 3 market intelligence feeds
RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed"
]

# 20 Unique high-quality crypto stock images
IMAGE_LIBRARY = [
    "https://images.unsplash.com/photo-1621416894569-0f39ed31d247?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1516245834210-c4c142787335?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1605792657660-596af9009e82?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1622630998477-20aa696ecb05?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1609554496796-c345a5335ceb?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1624996379697-f01d168b1a52?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1621504450181-5d156658e94a?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1620321023374-d1a68fbc720d?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1621504450081-3f191f635677?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1642104704074-907c0698cbd9?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1639762681057-408e52192e55?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1644361566696-3d442b5b482a?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1518546305927-5a555bb7020d?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1621761191319-c6fb62004040?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1590283603385-17ffb3a7f29f?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1640340434855-6084b1f4901c?w=600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1608222351212-18fe0ec7b13b?w=600&auto=format&fit=crop&q=80"
]

def clean_html(raw_html):
    """Strips messy HTML tags and leaves perfectly clean text strings."""
    if not raw_html:
        return ""
    clean = re.sub(r'<script.*?>.*?</script>', '', str(raw_html), flags=re.DOTALL)
    clean = re.sub(r'<style.*?>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = " ".join(clean.split())
    return clean.strip()

def send_to_telegram_channel(title, briefing, image_url, importance):
    """Pushes the top-ranked news directly to your Telegram audience."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram Alert: Credentials missing. Skipping broadcast.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    caption = (
        f"<b>⚡️ {title.upper()}</b>\n\n"
        f"<b>Market Briefing:</b>\n"
        f"{briefing}\n\n"
        f"<i>📊 Impact Priority: {importance}/10</i>"
    )

    payload = {
        "chat_id": chat_id,
        "photo": image_url,
        "caption": caption[:1000], 
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("-> Telegram broadcast successfully deployed!")
        else:
            print(f"-> Telegram Server Error: {response.text}")
    except Exception as e:
        print(f"-> Telegram Connection Failed: {e}")

def ask_gemini_ai(title, description):
    """Uses Gemini API to write a sharp, professional market summary."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    prompt = (
        f"Analyze this crypto news event:\n"
        f"Title: {title}\n"
        f"Context: {description[:300]}\n\n"
        f"Write a sharp 2-3 sentence market briefing analyzing this news for asset traders.\n"
        f"Do not use markdown formatting. Reply exactly in this structure:\n"
        f"SCORE: 7\n"
        f"SUMMARY: One sentence summary.\n"
        f"BRIEFING: Your multi-sentence briefing text goes here."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
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
    except Exception as e:
        print(f"-> Gemini API skipped due to timeout or error: {e}")
    
    return None

def run_scraper():
    print("Initializing Core Feed Scraper...")
    all_stories = []
    
    # Shuffle the image library so the rotation is completely random every run
    random.shuffle(IMAGE_LIBRARY)

    for feed_url in RSS_FEEDS:
        print(f"Fetching from: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            # Process up to 8 stories per feed to ensure we hit 20 total
            for entry in feed.entries[:8]:
                raw_title = entry.get("title", "")
                raw_desc = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Recent Sync")

                title = clean_html(raw_title)
                description = clean_html(raw_desc)

                print(f"Analyzing: {title[:40]}...")
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis:
                    importance = ai_analysis["importance"]
                    summary = ai_analysis["summary"]
                    briefing = ai_analysis["briefing"]
                else:
                    importance = 5
                    summary = title
                    briefing = description

                # Pulls a fresh image in order from the shuffled list
                assigned_image = IMAGE_LIBRARY[len(all_stories) % len(IMAGE_LIBRARY)]

                all_stories.append({
                    "title": title,
                    "link": link,
                    "time": published,
                    "importance": importance,
                    "summary": summary,
                    "briefing": briefing,
                    "image": assigned_image
                })
                time.sleep(1) 
        except Exception as e:
            print(f"Skipping stream conflict: {e}")

    if not all_stories:
        print("CRITICAL: No stories extracted. Database empty.")
        return

    # Sort strictly by highest importance score and pull EXACTLY 20 stories
    all_stories = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:20]

    # Save to the database
    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)
    print(f"Successfully saved {len(all_stories)} records to news.json.")

    # Grab the #1 story to blast to Telegram
    top_story = all_stories[0]
    print(f"\nTop Story: {top_story['title']} (Score: {top_story['importance']}/10)")
    
    send_to_telegram_channel(
        title=top_story["title"],
        briefing=top_story["briefing"],
        image_url=top_story["image"],
        importance=top_story["importance"]
    )

if __name__ == "__main__":
    run_scraper()
