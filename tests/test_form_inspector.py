"""
Test script to inspect DTEK form structure.
This will help us understand how to fill the form programmatically.
"""
import asyncio
from playwright.async_api import async_playwright


async def inspect_form():
    """Open DTEK page and inspect form structure."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Open visible browser
        page = await browser.new_page()

        print("Loading DTEK page...")
        await page.goto("https://www.dtek-dnem.com.ua/ua/shutdowns")

        # Wait for page to load
        await page.wait_for_load_state("networkidle")

        print("\n=== Form Structure Inspection ===\n")

        # Try to find form inputs
        print("Looking for form inputs...")

        # Check for input fields
        inputs = await page.query_selector_all("input")
        print(f"\nFound {len(inputs)} input elements:")
        for i, inp in enumerate(inputs[:10]):  # Limit to first 10
            input_type = await inp.get_attribute("type")
            input_name = await inp.get_attribute("name")
            input_id = await inp.get_attribute("id")
            input_placeholder = await inp.get_attribute("placeholder")
            input_class = await inp.get_attribute("class")

            print(f"\nInput {i+1}:")
            print(f"  Type: {input_type}")
            print(f"  Name: {input_name}")
            print(f"  ID: {input_id}")
            print(f"  Placeholder: {input_placeholder}")
            print(f"  Class: {input_class}")

        # Check for select dropdowns
        selects = await page.query_selector_all("select")
        print(f"\n\nFound {len(selects)} select elements:")
        for i, sel in enumerate(selects):
            select_name = await sel.get_attribute("name")
            select_id = await sel.get_attribute("id")
            select_class = await sel.get_attribute("class")

            print(f"\nSelect {i+1}:")
            print(f"  Name: {select_name}")
            print(f"  ID: {select_id}")
            print(f"  Class: {select_class}")

        # Try to find labels with text about address
        labels = await page.query_selector_all("label")
        print(f"\n\nFound {len(labels)} label elements:")
        for i, label in enumerate(labels[:10]):
            label_text = await label.text_content()
            label_for = await label.get_attribute("for")
            if any(word in label_text.lower() for word in ["адрес", "вулиц", "будинок", "місто"]):
                print(f"\nLabel {i+1}: {label_text}")
                print(f"  For: {label_for}")

        print("\n\n=== Page is open. Inspect in browser and press Enter to close ===")
        input()

        await browser.close()


if __name__ == "__main__":
    asyncio.run(inspect_form())
