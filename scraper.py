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
    """Sends headline to Gemini to generate Score, Summary, and a Unique Briefing."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    # Updated Prompt: Now explicitly asks for a 3-part response including the briefing
    prompt = (
        f"Analyze this crypto headline:\nTitle: {title}\nDescription: {description}\n\n"
        f"Provide your response in exactly this format, with no markdown, no code blocks, and no extra text:\n"
        f"Score || Summary || Briefing\n\n"
        f"Example:\n"
        f"7 || Bitcoin breaks key resistance level. || This breakout was triggered by massive institutional buying pressure on major exchanges. Traders should watch the next resistance zone closely, as high volatility is expected over the next 4 hours."
    )

    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        result = response.json()
        
        if "candidates" in result:
            raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Parse the 3 parts separated by "||"
            if "||" in raw_text:
                parts = raw_text.split("||")
                if len(parts) >= 3:
                    importance = int(parts[0].strip())
                    summary = parts[1].strip()
                    briefing = parts[2].strip()
                    return {"importance": importance, "summary": summary, "briefing": briefing}
    except Exception:
        pass
    return None

def run_scraper():
    print("Starting Premium Crypto News Robot...")
    all_stories = []

    for feed_url in RSS_FEEDS:
        print(f"Checking feed target: {feed_url}")
        try:
            feed = feedparser.parse(feed_url)
            # Increased to take the top 5 items per feed instead of 3
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                description = entry.get("summary", "")
                link = entry.get("link", "")
                published = entry.get("published", "Just now")

                print(f"Processing: {title[:50]}...")
                
                # Ask AI for the 3-part breakdown
                ai_analysis = ask_gemini_ai(title, description)
                
                # Check if AI successfully returned the dictionary with the briefing
                if ai_analysis and isinstance(ai_analysis, dict):
                    importance = ai_analysis.get("importance", 5)
                    summary = ai_analysis.get("summary", title)
                    briefing = ai_analysis.get("briefing", description)
                    print(f"-> AI Success! Score: {importance}")
                else:
                    importance = 5
                    summary = title 
                    briefing = description  # Fallback to standard description
                    print("-> AI skipped/limited. Applying database fallback safety.")

                all_stories.append({
                    "title": title,
                    "link": link,
                    "time": published,
                    "importance": int(importance),
                    "summary": summary,
                    "briefing": briefing
                })
                
                # Wait 2 seconds to protect free API thresholds
                time.sleep(2)
                
        except Exception as e:
            print(f"Error checking stream: {e}")

    if len(all_stories) == 0:
        print("Warning: No stories found in RSS feeds at all.")
    else:
        # Sort stories by highest importance score first and keep the top 15
        all_stories = sorted(all_stories, key=lambda x: x["importance"], reverse=True)[:15]

    with open("news.json", "w") as f:
        json.dump(all_stories, f, indent=4)
        
    print(f"\nFinished! Saved {len(all_stories)} entries directly into news.json.")

if __name__ == "__main__":
    run_scraper()
