"""
Test script to verify parser works correctly (full cycle).
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from parser import fetch_dtek_schedule


async def test_parser():
    """Test the complete parser cycle."""
    print("=" * 60)
    print("Testing DTEK Parser")
    print("=" * 60)

    try:
        print("\nFetching schedule for:")
        print("  City: Дніпро")
        print("  Street: Миру")
        print("  House: 4")
        print("\nThis will:")
        print("  1. Open DTEK website")
        print("  2. Fill the form")
        print("  3. Parse both schedule tables")
        print("  4. Return structured data")
        print("\nPlease wait...\n")

        # Fetch schedule (headless mode)
        # Note: Trying without prefixes like "м." or "Просп." first
        cache = await fetch_dtek_schedule(
            city="Дніпро",
            street="Миру",
            house_number="4",
            include_possible=True
        )

        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        print(f"\nActual Schedule (today/tomorrow): {len(cache.actual_schedules)} outages")
        if cache.actual_schedules:
            print("\nFirst 5 actual outages:")
            for schedule in cache.actual_schedules[:5]:
                print(f"  - {schedule}")
        else:
            print("  No actual outages found!")

        print(f"\nPossible Schedule (weekly): {len(cache.possible_schedules)} outages")
        if cache.possible_schedules:
            print("\nFirst 5 possible outages:")
            for schedule in cache.possible_schedules[:5]:
                print(f"  - {schedule}")
        else:
            print("  No possible outages found!")

        print(f"\nLast updated: {cache.last_updated}")

        print("\n" + "=" * 60)
        print("Test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n{'=' * 60}")
        print("ERROR")
        print("=" * 60)
        print(f"\n{e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_parser())
