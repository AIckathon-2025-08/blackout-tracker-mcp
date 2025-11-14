"""
Debug script to inspect page structure and find correct selectors.
Opens browser in visible mode and saves page HTML.
"""
import asyncio
from playwright.async_api import async_playwright


async def debug_page():
    """Debug DTEK page structure."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Loading DTEK page...")
        await page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns")
        await page.wait_for_load_state("networkidle")

        print("Page loaded. Waiting 5 seconds for JS to render...")
        await asyncio.sleep(5)

        # Save HTML to file
        html = await page.content()
        with open("dtek_page.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("\nSaved HTML to dtek_page.html")

        # Take screenshot
        await page.screenshot(path="dtek_page.png", full_page=True)
        print("Saved screenshot to dtek_page.png")

        # Print some selectors info
        print("\nChecking for input fields...")

        # Try different selectors for inputs
        all_inputs = await page.query_selector_all("input")
        print(f"Found {len(all_inputs)} input elements")

        for i, inp in enumerate(all_inputs[:5]):
            placeholder = await inp.get_attribute("placeholder")
            name = await inp.get_attribute("name")
            id_attr = await inp.get_attribute("id")
            is_visible = await inp.is_visible()
            print(f"\nInput {i+1}:")
            print(f"  Placeholder: {placeholder}")
            print(f"  Name: {name}")
            print(f"  ID: {id_attr}")
            print(f"  Visible: {is_visible}")

        print("\nDone! Check dtek_page.html and dtek_page.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(debug_page())
