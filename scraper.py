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
    """Removes HTML tags, image tags, and messy code blocks completely."""
    if not raw_html:
        return ""
    clean = re.sub(r'<script.*?>.*?</script>', '', raw_html, flags=re.DOTALL)
    clean = re.sub(r'<style.*?>.*?</style>', '', clean, flags=re.DOTALL)
    clean = re.sub(r'<[^>]+>', '', clean)
    clean = " ".join(clean.split())
    return clean.strip()

def ask_gemini_ai(title, description):
    """Sends clean data to Gemini and processes the response into structured segments."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    clean_title = clean_html(title)
    clean_desc = clean_html(description)[:300]

    prompt = (
        f"Analyze this crypto news headline:\n"
        f"Title: {clean_title}\n"
        f"Description: {clean_desc}\n\n"
        f"Provide a professional 2-3 sentence market briefing analyzing this news for crypto traders.\n"
        f"Your response must be standard text only. Do not use markdown, bullet points, or code blocks.\n"
        f"Reply using exactly this format:\n"
        f"SCORE: 7\n"
        f"SUMMARY: One sentence summary here.\n"
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

            # Parse lines using dynamic keyword hunting
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
        print(f"Gemini engine warning: {e}")
    return None

def run_scraper():
    print("Starting Mainframe Crypto News Terminal...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Reading channel: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"Warning: Stream {feed_url} empty or blocked.")
                continue

            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                # Master cleanup pass to strip all ugly raw HTML strings
                clean_title_str = clean_html(title)
                clean_desc_str = clean_html(description)

                print(f"Processing item: {clean_title_str[:40]}...")
                
                ai_analysis = ask_gemini_ai(clean_title_str, clean_desc_str)
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = ai_analysis.get("importance", 5)
                    summary = ai_analysis.get("summary", clean_title_str)
                    briefing = ai_analysis.get("briefing", clean_desc_str)
                else:
                    importance = 5
                    summary = clean_title_str
                    briefing = clean_desc_str

                all_stories.append({
                    "title": clean_title_str,
                    "link": link,
                    "time": published,
                    "importance": int(importance),
                    "summary": summary,
                    "briefing": briefing
                })
                time.sleep(1)
                
        except Exception as e:
            print(f"Channel error skipped: {e}")

    # Safety Net: If everything failed, populate dummy cards so frontend never freezes
    if len(all_stories) == 0:
        print("CRITICAL: All feeds failed to pull. Deploying live database safety net.")
        all_stories.append({
            "title": "Crypto Terminal Syncing Assets",
            "link": "https://cointelegraph.com",
            "time": "Just now",
            "importance": 5,
            "summary": "The live news terminal data streams are actively refreshing nodes.",
            "briefing": "The data feeds are currently syncing updates across global networks. Check back in 60 seconds."
        })

    # Sort stories by highest impact score first and trim to 15 items maximum
    all_stories = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:15]

    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)
        
    print(f"Success! {len(all_stories)} entries compiled successfully into news.json.")

if __name__ == "__main__":
    run_scraper()
