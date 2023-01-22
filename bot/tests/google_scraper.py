import asyncio
import os
print(os.listdir(os.getcwd()))

from modules.util.scraping.google import GoogleScraper
from playwright.async_api import async_playwright

print(os.getcwd())

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        scraper = GoogleScraper(browser)
        
        print(await scraper.search("sex"))
    
asyncio.run(main())