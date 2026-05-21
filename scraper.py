import os
import json
import re
import time
import feedparser
import requests

RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed"
]

def ask_gemini_ai(title, description):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing Gemini API Key!")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    prompt = (
        f"You are a crypto news editor. Analyze this headline:\n"
        f"Title: {title}\nDescription: {description}\n\n"
        f"Respond ONLY in this exact JSON format, nothing else:\n"
        f'{{"importance": 7, "summary": "A sharp two-sentence summary here"}}'
    )

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        if "error" in result:
            print(f"Google API Warning: {result['error'].get('message')}")
            return None
            
        if "candidates" not in result:
            return None
            
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as e:
        print(f"Parsing skipped: {e}")
        return None
    return None

def run_scraper():
    print("Starting Crypto Hub News Robot with safe rate-limiting...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Checking feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            # Pulling just the top 2 items per feed to respect free API limits
            for entry in feed.entries[:2]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"Processing headline: {title[:50]}...")
                
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = int(ai_analysis.get("importance", 5))
                    summary = ai_analysis.get("summary", "Market update processed.")
                    print(f"-> Saved! Score: {importance}/10")
                    
                    all_stories.append({
                        "title": title,
                        "link": link,
                        "time": published,
                        "importance": importance,
                        "summary": summary
                    })
                else:
                    print("-> Skipped due to rate limit or parsing.")
                
                # Crucial fix: Wait 3 seconds before hitting Google again
                time.sleep(3)
                
        except Exception as e:
            print(f"Error checking stream: {e}")

    # Save whatever successfully passed through the limit
    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)
        
    print(f"\nExecution finished! Saved {len(all_stories)} updates.")

if __name__ == "__main__":
    run_scraper()
