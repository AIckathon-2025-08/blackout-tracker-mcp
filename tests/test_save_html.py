"""
Test to save HTML after form fill to inspect table structure.
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from parser import DTEKParser


async def test_save_html():
    """Fill form and save HTML."""
    parser = DTEKParser(headless=True)

    try:
        await parser.start()
        await parser.page.goto(parser.DTEK_URL, wait_until="networkidle")
        await parser._close_modal_if_present()

        print("Filling form...")
        await parser._fill_address_form(
            city="Дніпро",
            street="Вʼячеслава Липинського",
            house_number="4"
        )

        print("Getting HTML...")
        html = await parser.page.content()

        print("Saving HTML...")
        with open("dtek_with_schedule.html", "w", encoding="utf-8") as f:
            f.write(html)

        print("Saved to dtek_with_schedule.html")

        # Also take screenshot
        await parser.page.screenshot(path="dtek_with_schedule.png", full_page=True)
        print("Screenshot saved to dtek_with_schedule.png")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await parser.close()


if __name__ == "__main__":
    asyncio.run(test_save_html())
