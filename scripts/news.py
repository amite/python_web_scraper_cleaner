from newspaper.google_news import GoogleNewsSource

source = GoogleNewsSource(
    country="US",
    period="1d",
    max_results=10,
)

source.build(top_news=True)

import subprocess
import json
import glob
import os

# Load existing URLs
output_dir = "data/news_output"
existing_urls = set()
if os.path.exists(output_dir):
    for json_file in glob.glob(os.path.join(output_dir, "*.json")):
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                if "url" in data:
                    existing_urls.add(data["url"])
        except Exception as e:
            print(f"Error reading {json_file}: {e}")

print(f"Found {len(existing_urls)} existing articles.")

found_urls = source.article_urls()
print(f"Found {len(found_urls)} articles from Google News.")

new_urls = [url for url in found_urls if url not in existing_urls]
print(f"Found {len(new_urls)} new articles to download (skipped {len(found_urls) - len(new_urls)}).")

for url in new_urls:
    print(f"Downloading {url}...")
    try:
        subprocess.run(
            ["/home/amite/code/python/scraper_cleaner/.venv/bin/trif", url, "--output-dir", output_dir],
            check=False,
            timeout=30
        )
    except subprocess.TimeoutExpired:
        print(f"Skipping {url} due to timeout.")
    except Exception as e:
        print(f"Error downloading {url}: {e}")