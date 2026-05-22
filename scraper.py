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

def clean_html(raw_html):
    """Removes HTML tags, image tags, and messy code blocks from RSS feeds."""
    if not raw_html:
        return ""
    # Remove script and style elements
    clean = re.sub(r'<script.*?>.*?</script>', '', raw_html, flags=re.DOTALL)
    clean = re.sub(r'<style.*?>.*?</style>', '', clean, flags=re.DOTALL)
    # Remove all standard HTML tags
    clean = re.sub(r'<[^>]+>', '', clean)
    # Fix excess whitespace layout characters
    clean = " ".join(clean.split())
    return clean.strip()

def ask_gemini_ai(title, description):
    """Sends clean data to Gemini and strictly extracts text fields."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    # Sanitize inputs before handing them to the AI engine
    clean_title = clean_html(title)
    clean_desc = clean_html(description)[:400] # Cap length to avoid token bloating

    prompt = (
        f"Analyze this crypto asset news item:\n"
        f"Headline: {clean_title}\n"
        f"Context: {clean_desc}\n\n"
        f"Write a professional, unique 2-3 sentence market briefing analyzing this news for traders.\n"
        f"Do not mention any HTML tags. Do not use code blocks.\n"
        f"Provide your response exactly like this template text format:\n"
        f"SCORE: 7\n"
        f"SUMMARY: Simple one sentence summary here.\n"
        f"BRIEFING: Your multi-sentence market analysis briefing text goes here."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        result = response.json()
        
        if "candidates" in result:
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            importance = 5
            summary = clean_title
            briefing = clean_desc

            # Parse lines robustly using text search keys
            for line in raw_text.split('\n'):
                if line.upper().startswith("SCORE:"):
                    try:
                        importance = int(line.split(":", 1)[1].strip())
                    except: pass
                elif line.upper().startswith("SUMMARY:"):
                    summary = line.split(":", 1)[1].strip()
                elif line.upper().startswith("BRIEFING:"):
                    briefing = line.split(":", 1)[1].strip()

            return {"importance": importance, "summary": summary, "briefing": briefing}
    except Exception as e:
        print(f"Gemini processing node error: {e}")
    return None

def run_scraper():
    print("Starting Sanitized Crypto News Terminal Robot...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Checking target stream: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"Processing: {title[:40]}...")
                
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = ai_analysis.get("importance", 5)
                    summary = ai_analysis.get("summary", clean_html(title))
                    briefing = ai_analysis.get("briefing", clean_html(description))
                    print(f"-> Success! Generated Unique AI Briefing.")
                else:
                    importance = 5
                    summary = clean_html(title)
                    briefing = clean_html(description)
                    print("-> Fallback used. Feed description cleaned automatically.")

                all_stories.append({
                    "title": clean_html(title),
                    "link": link,
                    "time": published,
                    "importance": int(importance),
                    "summary": summary,
                    "briefing": briefing
                })
                
                time.sleep(2)
                
        except Exception as e:
            print(f"Stream error: {e}")

    if len(all_stories) == 0:
        print("Empty array stream generated.")
    else:
        all_stories = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:15]

    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)
        
    print(f"\nSaved {len(all_stories)} perfectly cleaned nodes into news.json.")

if __name__ == "__main__":
    run_scraper()
