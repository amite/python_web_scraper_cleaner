import trafilatura
import json
import os
import re
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

def scrape_article_with_trafilatura(url):
    """
    Scrape article using Trafilatura library
    Returns structured data and clean text
    """
    try:
        # Download the webpage
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            return None, "Error: Could not download the webpage"
        
        # Extract with metadata as JSON
        result_json = trafilatura.extract(
            downloaded,
            output_format='json',
            with_metadata=True,
            include_comments=False,
            include_tables=True,
            include_images=True,  # Set to True if you want image URLs
            include_links=True
        )
        
        if not result_json:
            return None, "Error: Could not extract article content"
        
        # Parse the JSON result
        article_data = json.loads(result_json)
        
        # Extract plain text version
        text_content = trafilatura.extract(
            downloaded,
            output_format='txt',
            with_metadata=False,
            include_comments=False
        )
        
        # Structure the data in a consistent format
        structured_data = {
            "url": url,
            "scraped_at": datetime.now().isoformat(),
            "title": article_data.get("title"),
            "author": article_data.get("author"),
            "date": article_data.get("date"),
            "sitename": article_data.get("sitename"),
            "hostname": article_data.get("hostname"),
            "description": article_data.get("description"),
            "categories": article_data.get("categories", []),
            "tags": article_data.get("tags", []),
            "fingerprint": article_data.get("fingerprint"),
            "language": article_data.get("language"),
            "text": article_data.get("text"),
            "raw_text": text_content,
            "source": article_data.get("source"),
            "source_hostname": article_data.get("source-hostname")
        }
        
        return structured_data, text_content
        
    except Exception as e:
        return None, f"Error: {str(e)}"

def format_article_markdown(data, text):
    """Format the article data into readable markdown"""
    markdown_parts = []
    
    if data.get("title"):
        markdown_parts.append(f"# {data['title']}\n")
    
    if data.get("author"):
        markdown_parts.append(f"**Author:** {data['author']}")
    
    if data.get("date"):
        markdown_parts.append(f"**Published:** {data['date']}")
    
    if data.get("sitename"):
        markdown_parts.append(f"**Source:** {data['sitename']}")
    
    if data.get("description"):
        markdown_parts.append(f"\n## Summary\n{data['description']}\n")
    
    if data.get("categories"):
        markdown_parts.append(f"**Categories:** {', '.join(data['categories'])}")
    
    if data.get("tags"):
        markdown_parts.append(f"**Tags:** {', '.join(data['tags'])}")
    
    markdown_parts.append(f"\n---\n\n## Article Content\n\n{text}")
    
    return '\n'.join(markdown_parts)

def main():
    url = "https://scroll.in/latest/1081286/madhya-pradesh-nine-arrested-after-communal-clashes-in-guna"
    
    print("Scraping article with Trafilatura...")
    print(f"URL: {url}\n")
    
    # Scrape the article
    article_data, text_content = scrape_article_with_trafilatura(url)
    
    if article_data is None:
        print(f"Failed to scrape: {text_content}")
        return
    
    # Create output directory
    os.makedirs('data', exist_ok=True)

    # Create slugged filename from title
    title_slug = slugify(article_data.get('title', 'untitled-article'))

    # Save structured JSON
    json_path = f'data/{title_slug}.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(article_data, f, indent=2, ensure_ascii=False)
    print(f"✓ Structured JSON saved to {json_path}")

    # Save formatted markdown
    markdown_content = format_article_markdown(article_data, text_content)
    md_path = f'data/{title_slug}.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"✓ Formatted markdown saved to {md_path}")

    # Save plain text
    txt_path = f'data/{title_slug}.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        if text_content is not None:
            f.write(text_content)
        else:
            f.write("Error: Could not extract plain text content")
    print(f"✓ Plain text saved to {txt_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("ARTICLE SUMMARY")
    print("="*60)
    print(f"Title: {article_data.get('title', 'N/A')}")
    print(f"Author: {article_data.get('author', 'N/A')}")
    print(f"Published: {article_data.get('date', 'N/A')}")
    print(f"Source: {article_data.get('sitename', 'N/A')}")
    print(f"Language: {article_data.get('language', 'N/A')}")
    
    if article_data.get('categories'):
        print(f"Categories: {', '.join(article_data['categories'])}")
    
    if article_data.get('tags'):
        print(f"Tags: {', '.join(article_data['tags'])}")
    
    text_length = len(text_content) if text_content else 0
    word_count = len(text_content.split()) if text_content else 0
    print(f"\nText length: {text_length} characters")
    print(f"Word count: ~{word_count} words")
    
    print("\n" + "="*60)
    print("PREVIEW (first 500 characters)")
    print("="*60)
    if text_content:
        print(text_content[:500] + "...\n")
    else:
        print("Error: No text content available for preview\n")

if __name__ == "__main__":
    main()