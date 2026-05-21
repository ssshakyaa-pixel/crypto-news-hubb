import os
import json
import feedparser
import requests

# 1. The list of crypto news feeds we want to listen to
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

    # Secure endpoint URL configuration passing the password directly
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    prompt = (
        f"You are a crypto news editor. Analyze this headline and description:\n"
        f"Title: {title}\nDescription: {description}\n\n"
        f"Task:\n"
        f"1. Rate the importance of this news from 1 to 10 (10 being market-changing like BTC hitting a new ATH).\n"
        f"2. Summarize it clearly in exactly 2 sentences.\n"
        f"Respond ONLY in this exact JSON format, nothing else:\n"
        f'{{"importance": 8, "summary": "Your 2-sentence summary here"}}'
    )

    data = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        # Safe log parsing to spot any active authentication locks
        if "candidates" not in result:
            print(f"Gemini API Error Response: {result}")
            return None
            
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        
        # Clean up any potential markdown wrapper code formatting if Gemini adds it
        if raw_text.startswith("```json"):
            raw_text = raw_text.replace("```json", "").replace("```", "").strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.replace("```", "").strip()
            
        return json.loads(raw_text)
    except Exception as e:
        print(f"AI processing failed parsing layout: {e}")
        return None

def run_scraper():
    print("Starting Crypto Hub News Robot...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Checking feed: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:5]:  # Look at the top 5 freshest articles
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"\nNew headline found: {title}")
                print("Asking Gemini AI to evaluate...")
                
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = int(ai_analysis.get("importance", 1))
                    summary = ai_analysis.get("summary", "No summary provided.")
                    
                    print(f"-> Success! Importance Score: {importance}/10")
                    
                    # Store everything matching our database layout
                    all_stories.append({
                        "title": title,
                        "link": link,
                        "time": published,
                        "importance": importance,
                        "summary": summary
                    })
                else:
                    print("-> Skipped item due to processing issue.")
        except Exception as e:
            print(f"Error checking stream link {feed_url}: {e}")

    # Keep only important entries and sort by highest market weight
    important_stories = [s for s in all_stories if s["importance"] >= 4]
    important_stories = sorted(important_stories, key=lambda x: x["importance"], reverse=True)[:10]

    # Write data straight to our local file layout
    with open("news.json", "w") as f:
        json.dump(important_stories, f, indent=4)
        
    print(f"\nExecution finished! Saved {len(important_stories)} updates to database.")

if __name__ == "__main__":
    run_scraper()
