
import json
import urllib.request
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
    request = urllib.request.Request(
        feed["url"],
        headers={"User-Agent": "BanglaNewsAI/1.0"}
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())

    items = []

    for item in root.findall(".//item"):
        title = item.findtext("title", default="").strip()
        link = item.findtext("link", default="").strip()
        description = item.findtext("description", default="").strip()
        pub_date = item.findtext("pubDate", default="").strip()

        if title and link:
            items.append({
                "source": feed["name"],
                "title": title,
                "link": link,
                "description": description,
                "published": pub_date
            })

    return items

def main():
    news = []
    errors = []

    for feed in FEEDS:
        try:
            news.extend(fetch_feed(feed))
            print("Fetched:", feed["name"])
        except Exception as error:
            errors.append(feed["name"])
            print("Feed unavailable:", feed["name"], str(error))

    # Remove duplicate links
    unique = {}
    for item in news:
        unique[item["link"]] = item

    result = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(unique),
        "news": list(unique.values())[:50],
        "feed_errors": errors
    }

    with open("news.json", "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    print("Total unique news:", result["count"])

if __name__ == "__main__":
    main()
