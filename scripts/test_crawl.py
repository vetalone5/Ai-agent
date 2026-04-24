"""Quick crawl test on example.com."""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.crawler import Crawler

async def main():
    print("Crawling example.com...")
    crawler = Crawler(base_url="https://example.com", max_pages=3)
    pages = await crawler.crawl_site()
    print(f"Found {len(pages)} pages\n")
    for p in pages:
        print(f"URL: {p['url']}")
        print(f"  Status: {p.get('status_code')}")
        print(f"  Title: {p.get('title', '-')[:60]}")
        print(f"  H1: {p.get('h1', '-')[:60]}")
        print(f"  Words: {p.get('word_count', 0)}")
        issues = p.get("issues", [])
        print(f"  Issues: {len(issues)}")
        for issue in issues:
            print(f"    [{issue['severity']}] {issue['type']}: {issue.get('detail','')}")

if __name__ == "__main__":
    asyncio.run(main())
