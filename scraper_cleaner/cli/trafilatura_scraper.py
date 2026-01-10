import json
import os
import re
import logging
import argparse
from datetime import datetime


def scrape_article_with_trafilatura(url):
    """
    Scrape article using Trafilatura library
    Returns structured data and clean text
    """
    try:
        try:
            import trafilatura
        except ModuleNotFoundError as e:
            error_msg = (
                "Missing dependency 'trafilatura'. Install it and retry "
                "(e.g. `pip install trafilatura`)."
            )
            logging.error(error_msg)
            return None, error_msg

        logging.info(f"Starting scrape job for URL: {url}")

        # Set up headers with User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.google.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Download the webpage with custom headers
        try:
            # First try with trafilatura's built-in fetch
            downloaded = trafilatura.fetch_url(url)

            # If trafilatura fails, try with requests library
            if not downloaded:
                try:
                    import requests

                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    downloaded = response.text
                    logging.info(
                        f"Downloaded {url} using requests with custom User-Agent"
                    )
                except Exception as e:
                    error_msg = (
                        f"Both trafilatura and requests failed to download: {str(e)}"
                    )
                    logging.error(f"Download failed for {url}: {error_msg}")
                    return None, error_msg
        except Exception as e:
            error_msg = f"Download error: {str(e)}"
            logging.error(f"Download exception for {url}: {error_msg}")
            return None, error_msg

        # Extract with metadata as JSON
        try:
            result_json = trafilatura.extract(
                downloaded,
                output_format="json",
                with_metadata=True,
                include_comments=False,
                include_tables=True,
                include_images=False,  # Set to True if you want image URLs
                include_links=False,
            )

            if not result_json:
                error_msg = "Could not extract article content"
                logging.error(f"Extraction failed for {url}: {error_msg}")
                return None, error_msg
        except Exception as e:
            error_msg = f"Extraction error: {str(e)}"
            logging.error(f"Extraction exception for {url}: {error_msg}")
            return None, error_msg

        # Parse the JSON result
        try:
            article_data = json.loads(result_json)
        except Exception as e:
            error_msg = f"JSON parsing error: {str(e)}"
            logging.error(f"JSON parsing failed for {url}: {error_msg}")
            return None, error_msg

        # Extract plain text version
        try:
            text_content = trafilatura.extract(
                downloaded, output_format="txt", with_metadata=False, include_comments=False
            )
        except Exception as e:
            error_msg = f"Text extraction error: {str(e)}"
            logging.error(f"Text extraction failed for {url}: {error_msg}")
            return None, error_msg

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
            "source_hostname": article_data.get("source-hostname"),
        }

        logging.info(f"Successfully scraped article from {url}")
        return structured_data, text_content

    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(f"Unexpected error scraping {url}: {error_msg}")
        return None, error_msg


def slugify(text):
    """Convert text to a URL-friendly slug"""
    if not text:
        return "untitled"

    # Convert to lowercase
    slug = text.lower()

    # Remove special characters and replace spaces with underscores
    slug = re.sub(r"[^\w\s-]", "", slug)  # Remove special chars
    slug = re.sub(r"[\s]+", "_", slug)  # Replace spaces with underscores
    slug = re.sub(r"[-]+", "_", slug)  # Replace multiple hyphens with single underscore

    # Remove leading/trailing underscores
    slug = slug.strip("_")

    # Limit length to reasonable size
    if len(slug) > 100:
        slug = slug[:100]

    return slug or "untitled"


def reflow_text_to_markdown_paragraphs(
    text, *, max_sentences_per_paragraph=4, max_chars_per_paragraph=900
):
    """
    Convert trafilatura plain-text output into nicer Markdown paragraphs.

    Trafilatura often returns one sentence per line. In Markdown, single newlines
    are rendered as spaces, so we reflow lines into paragraphs separated by blank
    lines (double newlines).
    """
    if not text:
        return ""

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    raw_lines = [ln.strip() for ln in text.split("\n")]

    # If the text already contains blank lines, treat them as paragraph breaks
    if any(ln == "" for ln in raw_lines):
        paragraphs = []
        buf = []
        for ln in raw_lines:
            if ln == "":
                if buf:
                    paragraphs.append(" ".join(buf).strip())
                    buf = []
                continue
            buf.append(ln)
        if buf:
            paragraphs.append(" ".join(buf).strip())
        return "\n\n".join(p for p in paragraphs if p).strip()

    # Otherwise, create readable paragraphs by grouping consecutive lines
    lines = [ln for ln in raw_lines if ln]
    paragraphs = []
    buf = []
    sentence_count = 0
    char_count = 0

    for ln in lines:
        buf.append(ln)
        sentence_count += 1
        char_count += len(ln) + 1

        if (
            sentence_count >= max_sentences_per_paragraph
            or char_count >= max_chars_per_paragraph
        ):
            paragraphs.append(" ".join(buf).strip())
            buf = []
            sentence_count = 0
            char_count = 0

    if buf:
        paragraphs.append(" ".join(buf).strip())

    return "\n\n".join(p for p in paragraphs if p).strip()


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
        categories = data["categories"]
        # Ensure categories is a list
        if isinstance(categories, str):
            categories = [categories]
        markdown_parts.append(f"**Categories:** {', '.join(categories)}")

    if data.get("tags"):
        tags = data["tags"]
        # Ensure tags is a list
        if isinstance(tags, str):
            tags = [tags]
        markdown_parts.append(f"**Tags:** {', '.join(tags)}")

    formatted_text = reflow_text_to_markdown_paragraphs(text)
    markdown_parts.append(f"\n---\n\n## Article Content\n\n{formatted_text}")

    return "\n".join(markdown_parts)


def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()],
    )


def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="trafilatura_scraper.py",
        description="Scrape an article URL using Trafilatura and save JSON/Markdown/Text outputs.",
        epilog=(
            "Examples:\n"
            "  uv run scripts/trafilatura_scraper.py https://example.com/article\n"
            "  uv run scripts/trafilatura_scraper.py https://example.com/article --output-dir data/output\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Article URL to scrape. If omitted, you'll be prompted.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.path.join("data", "output"),
        help="Directory to write output files (default: %(default)s).",
    )
    return parser


def _is_exit_command(text: str) -> bool:
    return text.strip().lower() in {"/quit", "/exit"}


def main(argv=None):
    # Setup logging
    setup_logging()

    args = build_arg_parser().parse_args(argv)

    # Get URL from args, or prompt interactively
    url = (args.url or "").strip()
    if not url:
        url = input("Enter the URL to scrape: ").strip()
    if url and _is_exit_command(url):
        print("Exiting.")
        logging.info("User requested exit")
        return
    if not url:
        print("Error: No URL provided")
        logging.error("No URL provided by user")
        return

    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logging.info(f"Starting job {job_id} for URL: {url}")
    print("Scraping article with Trafilatura...")
    print(f"URL: {url}")
    print(f"Job ID: {job_id}\n")

    # Scrape the article
    article_data, text_content = scrape_article_with_trafilatura(url)

    if article_data is None:
        error_msg = f"Failed to scrape: {text_content}"
        logging.error(f"Job {job_id} failed: {error_msg}")
        print(error_msg)
        return

    logging.info(f"Job {job_id} successfully scraped article")

    # Create output directory
    try:
        output_dir = args.output_dir
        os.makedirs(output_dir, exist_ok=True)
        logging.info(f"Job {job_id} ensured output directory exists: {output_dir}")
    except Exception as e:
        error_msg = f"Failed to create output directory: {str(e)}"
        logging.error(f"Job {job_id} directory creation failed: {error_msg}")
        print(error_msg)
        return

    # Generate slug from article title
    article_title = article_data.get("title", "untitled_article")
    slug = slugify(article_title)

    # Save structured JSON
    try:
        json_path = os.path.join(output_dir, f"{slug}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(article_data, f, indent=2, ensure_ascii=False)
        logging.info(f"Job {job_id} saved structured JSON to {json_path}")
        print(f"✓ Structured JSON saved to {json_path}")
    except Exception as e:
        error_msg = f"Failed to save JSON: {str(e)}"
        logging.error(f"Job {job_id} JSON save failed: {error_msg}")
        print(f"✗ Failed to save JSON: {error_msg}")

    # Save formatted markdown
    try:
        markdown_content = format_article_markdown(article_data, text_content)
        md_path = os.path.join(output_dir, f"{slug}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logging.info(f"Job {job_id} saved formatted markdown to {md_path}")
        print(f"✓ Formatted markdown saved to {md_path}")
    except Exception as e:
        error_msg = f"Failed to save markdown: {str(e)}"
        logging.error(f"Job {job_id} markdown save failed: {error_msg}")
        print(f"✗ Failed to save markdown: {error_msg}")

    # Save plain text
    try:
        txt_path = os.path.join(output_dir, f"{slug}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            if text_content:
                f.write(text_content)
            else:
                f.write("")
        logging.info(f"Job {job_id} saved plain text to {txt_path}")
        print(f"✓ Plain text saved to {txt_path}")
    except Exception as e:
        error_msg = f"Failed to save text: {str(e)}"
        logging.error(f"Job {job_id} text save failed: {error_msg}")
        print(f"✗ Failed to save text: {error_msg}")

    # Print summary
    print("\n" + "=" * 60)
    print("ARTICLE SUMMARY")
    print("=" * 60)
    print(f"Title: {article_data.get('title', 'N/A')}")
    print(f"Author: {article_data.get('author', 'N/A')}")
    print(f"Published: {article_data.get('date', 'N/A')}")
    print(f"Source: {article_data.get('sitename', 'N/A')}")
    print(f"Language: {article_data.get('language', 'N/A')}")

    if article_data.get("categories"):
        print(f"Categories: {', '.join(article_data['categories'])}")

    if article_data.get("tags"):
        print(f"Tags: {', '.join(article_data['tags'])}")

    if text_content:
        print(f"\nText length: {len(text_content)} characters")
        print(f"Word count: ~{len(text_content.split())} words")

        print("\n" + "=" * 60)
        print("PREVIEW (first 500 characters)")
        print("=" * 60)
        print(text_content[:500] + "...\n")
    else:
        print("\nNo text content available for preview")

    logging.info(f"Job {job_id} completed successfully")


if __name__ == "__main__":
    main()
