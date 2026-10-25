
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS = [
    {
        "name": "BBC Bangla",
        "url": "https://feeds.bbci.co.uk/bengali/rss.xml"
    },
    {
        "name": "Google News Bangladesh",
        "url": "https://news.google.com/rss?hl=bn&gl=BD&ceid=BD:bn"
    }
]

def fetch_feed(feed):
    req = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "BanglaNewsAI/1.0"}
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        root = ET.fromstring(response.read())

    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        desc = item.findtext("description", default="").strip()
        published = item.findtext("pubDate", default="").strip()

        if title and link:
            items.append({
                "source": feed["name"],
                "title": title,
                "link": link,
                "description": desc[:1200],
                "published": published
            })

    return items

def list_gemini_models(api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    req = urllib.request.Request(
        url,
        headers={"x-goog-api-key": api_key}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read())
    for model in data.get("models", []):
        if "generateContent" in model.get("supportedGenerationMethods", []):
            print("Available Gemini model:", model["name"])

def make_ai_draft(item, api_key):
    prompt = f"""
তুমি Bangla News AI-এর বাংলা সংবাদ-সম্পাদক।

নিচের তথ্যের ভিত্তিতে একটি সংক্ষিপ্ত বাংলা সংবাদ-খসড়া তৈরি করো।
তথ্যে নেই এমন ঘটনা, সংখ্যা, উদ্ধৃতি বা দাবি যোগ করবে না।
তথ্য অসম্পূর্ণ হলে তা স্পষ্ট রাখবে।
মূল সংবাদমাধ্যমের লেখা হুবহু কপি করবে না।
খসড়াটি প্রকাশের আগে মানুষের যাচাই প্রয়োজন।

উৎস: {item['source']}
শিরোনাম: {item['title']}
সংক্ষিপ্ত বিবরণ: {item['description']}

শুধু বাংলায় ২-৪ বাক্যের একটি সারাংশ লেখো।
"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        "models/gemini-3.8-flash:generateContent?"
        + urllib.parse.urlencode({"key": api_key})
    )

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 300
        }
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read())

    return result["candidates"][0]["content"]["parts"][0]["text"].strip()

def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        list_gemini_models(api_key)

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY secret পাওয়া যায়নি")

    news = []
    errors = []

    for feed in FEEDS:
        try:
            news.extend(fetch_feed(feed))
            print("Fetched:", feed["name"])
        except Exception as error:
            errors.append(feed["name"])
            print("Feed unavailable:", feed["name"], str(error))

    unique = {}
    for item in news:
        unique[item["link"]] = item

    articles = list(unique.values())[:5]
    drafts = []

    
    for item in articles:
        try:
            summary = make_ai_draft(item, api_key)
            drafts.append({
                **item,
                "ai_summary": summary,
                "approval_status": "pending"
            })
            print("Draft created for:", item["title"])

        except Exception as error:
            if isinstance(error, urllib.error.HTTPError):
                details = error.read().decode("utf-8", errors="replace")
                print("AI draft failed:", item["title"], error.code, details)
            else:
                print("AI draft failed:", item["title"], repr(error))



    with open("news.json", "w", encoding="utf-8") as file:
        json.dump({
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "count": len(unique),
            "news": list(unique.values())[:50],
            "feed_errors": errors
        }, file, ensure_ascii=False, indent=2)

    with open("drafts.json", "w", encoding="utf-8") as file:
        json.dump({
            "created_at": datetime.now(timezone.utc).isoformat(),
            "count": len(drafts),
            "drafts": drafts
        }, file, ensure_ascii=False, indent=2)

    print("News collected:", len(unique))
    print("AI drafts created:", len(drafts))

if __name__ == "__main__":
    main()
