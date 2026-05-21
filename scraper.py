import os
import json
import time
import feedparser
import requests

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed"
]

def ask_gemini_ai(title, description):
    """Sends headline to Gemini using a clean, standard text request format."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing Gemini API Key!")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    # We ask Gemini to give us clean text separated by a special divider symbol (||)
    prompt = (
        f"Analyze this crypto headline:\nTitle: {title}\nDescription: {description}\n\n"
        f"Provide your response in exactly this format, with no markdown, no code blocks, and no extra text:\n"
        f"Score || Summary\n\n"
        f"Example:\n"
        f"7 || Bitcoin breaks key resistance level and targets new highs."
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if "candidates" not in result:
            return None
            
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Split the text by our custom divider symbol
        if "||" in raw_text:
            parts = raw_text.split("||")
            importance = int(parts[0].strip())
            summary = parts[1].strip()
            return {"importance": importance, "summary": summary}
            
    except Exception:
        pass
    return None

def run_scraper():
    print("Starting Simplified Crypto Hub News Robot...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Checking feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            # Process the top 3 freshest items from each source
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"Processing: {title[:50]}...")
                
                ai_analysis = ask_gemini_ai(title, description)
                
                # If AI works, use it. If it fails, keep the story anyway using a default score!
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = ai_analysis.get("importance", 5)
                    summary = ai_analysis.get("summary", title)
                    print(f"-> AI Parsed successfully! Score: {importance}")
                else:
                    importance = 5
                    summary = title
                    print("-> AI skipped or limited, using fallback layout.")

                all_stories.append({
                    "title": title,
                    "link": link,
                    "time": published,
                    "importance": int(importance),
                    "summary": summary
                })
                
                # Wait 2 seconds between requests to protect your rate limits
                time.sleep(2)
                
        except Exception as e:
            print(f"Error checking stream: {e}")

    # Sort stories by highest importance score first
    final_list = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:10]

    with open("news.json", "w") as f:
        json.dump(final_list, f, indent=4)
        
    print(f"\nFinished! Saved {len(final_list)} entries directly into news.json.")

if __name__ == "__main__":
    run_scraper()
