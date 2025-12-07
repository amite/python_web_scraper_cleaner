import requests
import os
import json
import re
from bs4 import BeautifulSoup
from datetime import datetime

def slugify(text):
    """Convert text to a URL/filename slug"""
    if not text:
        return "untitled"

    # Convert to lowercase
    slug = text.lower()

    # Remove special characters and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)  # Remove special chars
    slug = re.sub(r'[\s]+', '-', slug)     # Replace spaces with hyphens
    slug = re.sub(r'[-]+', '-', slug)      # Remove duplicate hyphens

    # Remove leading/trailing hyphens
    slug = slug.strip('-')

    # Limit length to reasonable filename length
    slug = slug[:80]

    return slug

def fetch_and_clean_url(url):
    try:
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the main article container
        article = soup.find('article', class_='scroll-article')
        if not article:
            return None, "Error: Could not find article content"

        # Initialize structured data
        article_data = {
            "url": url,
            "scraped_at": datetime.now().isoformat(),
            "category": None,
            "headline": None,
            "subheadline": None,
            "author": None,
            "published_date": None,
            "published_date_raw": None,
            "image_caption": None,
            "body_paragraphs": [],
            "tags": [],
            "full_text": None
        }

        # Extract article components
        content_parts = []

        # 1. Get the category/tag
        tag = article.find('span', class_='orange-tag')
        if tag:
            category_text = tag.get_text(strip=True)
            article_data["category"] = category_text
            content_parts.append(category_text)
            content_parts.append('')  # Empty line

        # 2. Get the headline
        h1 = article.find('h1')
        if h1:
            headline_text = h1.get_text(strip=True)
            article_data["headline"] = headline_text
            content_parts.append(headline_text)

        # 3. Get the subheadline
        h2 = article.find('h2')
        if h2:
            subheadline_text = h2.get_text(strip=True)
            article_data["subheadline"] = subheadline_text
            content_parts.append(subheadline_text)

        # 4. Get author and date
        author = article.find('address')
        if author:
            author_text = author.get_text(strip=True)
            article_data["author"] = author_text
            content_parts.append(author_text)

        time_container = article.find('div', class_='article-time-container')
        if time_container:
            time_elem = time_container.find('time', class_='article-published-time')
            if time_elem:
                published_text = time_elem.get_text(strip=True)
                article_data["published_date"] = published_text
                content_parts.append(published_text)
                
                # Get ISO datetime if available
                datetime_attr = time_elem.get('datetime')
                if datetime_attr:
                    article_data["published_date_raw"] = datetime_attr

        content_parts.append('')  # Empty line before image

        # 5. Get featured image caption
        featured_image = article.find('figure', class_='featured-image')
        if featured_image:
            figcaption = featured_image.find('figcaption')
            if figcaption:
                # Extract text parts and clean them
                caption_parts = [part.strip() for part in figcaption.stripped_strings]
                # Join non-empty parts with separator
                caption_text = ' | '.join(part for part in caption_parts if part)
                if caption_text:
                    article_data["image_caption"] = caption_text
                    content_parts.append(caption_text)

        # 6. Get the article body
        article_body = article.find('div', id='article-contents')
        if article_body:
            # Process paragraphs while preserving structure
            for element in article_body.find_all(['p', 'hr']):
                if element.name == 'hr':
                    content_parts.append('---')
                else:
                    text = element.get_text(strip=True)
                    if text:
                        article_data["body_paragraphs"].append(text)
                        content_parts.append(text)

        # 7. Get article tags
        tags_list = article.find('ul', class_='article-tags-list')
        if tags_list:
            tags = [tag.get_text(strip=True) for tag in tags_list.find_all('a')]
            article_data["tags"] = tags

        # Join with natural line breaks for full text
        clean_text = '\n'.join(content_parts)
        article_data["full_text"] = clean_text

        return article_data, clean_text

    except Exception as e:
        return None, f"Error: {str(e)}"

def save_html(url):
    """Save raw HTML for reference"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Create directory if it doesn't exist
        os.makedirs('data/html', exist_ok=True)

        # Save raw HTML
        html_filename = f"data/html/{url.replace('https://', '').replace('/', '_').replace('?', '_').replace('=', '_')}.html"
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Raw HTML saved to {html_filename}")
        return True

    except Exception as e:
        print(f"Error saving raw HTML: {str(e)}")
        return False

if __name__ == "__main__":
    url = "https://scroll.in/latest/1081286/madhya-pradesh-nine-arrested-after-communal-clashes-in-guna"

    # Save raw HTML
    save_html(url)

    # Process and extract structured content
    article_data, clean_content = fetch_and_clean_url(url)
    
    if article_data is None:
        print(f"Error: {clean_content}")
        exit(1)
    
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Create slugged filename from headline
    headline_slug = slugify(article_data['headline'])
    md_filename = f"data/{headline_slug}.md"
    json_filename = f"data/{headline_slug}.json"

    # Save clean text
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(f"# Cleaned Content from {url}\n\n")
        f.write(clean_content)
    print(f"Cleaned content saved to {md_filename}")

    # Save structured JSON
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, indent=2, ensure_ascii=False)
    print(f"Structured data saved to {json_filename}")

    # Print preview
    print("\nPreview:")
    print("-" * 50)
    print(clean_content[:500] + "...")
    print("\n" + "-" * 50)
    print("\nStructured Data Summary:")
    print(f"Headline: {article_data['headline']}")
    print(f"Author: {article_data['author']}")
    print(f"Published: {article_data['published_date']}")
    print(f"Category: {article_data['category']}")
    print(f"Paragraphs: {len(article_data['body_paragraphs'])}")
    print(f"Tags: {', '.join(article_data['tags'])}")