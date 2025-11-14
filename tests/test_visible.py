"""
Test with visible browser to see what's happening.
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from parser import DTEKParser


async def test_visible():
    """Test with visible browser."""
    parser = DTEKParser(headless=False)  # VISIBLE browser

    try:
        print("Starting browser (visible mode)...")
        await parser.start()

        print("Navigating to DTEK...")
        await parser.page.goto(parser.DTEK_URL, wait_until="networkidle")

        print("Closing modal...")
        await parser._close_modal_if_present()

        print("\nNow filling form. Watch the browser!")
        print("Trying city: Дніпро (without 'м.')")

        await parser._fill_address_form(
            city="Дніпро",  # Without prefix
            street="Миру",   # Without prefix
            house_number="4"
        )

        print("\nForm filled! Browser will stay open.")
        print("Press Enter to close...")
        input()

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print("\nBrowser will stay open. Press Enter to close...")
        input()
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(test_visible())
