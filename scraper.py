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
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Missing Gemini API Key!")
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Force Gemini to return pure JSON that matches our exact schema structure
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Analyze this crypto news item.\nTitle: {title}\nDescription: {description}"
            }]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "importance": {
                        "type": "INTEGER",
                        "description": "Rate the importance of this news from 1 to 10."
                    },
                    "summary": {
                        "type": "STRING",
                        "description": "A precise summary of the news in exactly two sentences."
                    }
                },
                "required": ["importance", "summary"]
            }
        }
    }

    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=12)
        result = response.json()
        
        if "error" in result:
            print(f"Google API Error: {result['error'].get('message')}")
            return None
            
        # Because we enforced the schema, this text is guaranteed to be clean JSON
        raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        return json.loads(raw_text)
        
    except Exception as e:
        print(f"Skipped article due to network/parsing exception: {e}")
        return None

def run_scraper():
    print("Starting Crypto Hub News Robot...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"\nChecking feed target: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            # Process the top 3 freshest items from each source
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"Processing headline: {title[:60]}...")
                
                ai_analysis = ask_gemini_ai(title, description)
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = int(ai_analysis.get("importance", 5))
                    summary = ai_analysis.get("summary", "Market update processed.")
                    print(f"-> SUCCESS! Importance: {importance}/10")
                    
                    all_stories.append({
                        "title": title,
                        "link": link,
                        "time": published,
                        "importance": importance,
                        "summary": summary
                    })
                else:
                    print("-> Article skipped.")
                
                # A safe 3-second delay to protect your free tier API limit
                time.sleep(3)
                
        except Exception as e:
            print(f"Error reading feed {feed_url}: {e}")

    # Sort stories so the highest importance items sit right at the top
    final_list = sorted(all_stories, key=lambda x: x.get("importance", 0), reverse=True)[:10]

    with open("news.json", "w") as f:
        json.dump(final_list, f, indent=4)
        
    print(f"\nExecution finished! Saved {len(final_list)} entries directly into news.json.")

if __name__ == "__main__":
    run_scraper()
