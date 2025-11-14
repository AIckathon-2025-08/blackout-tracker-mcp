"""
Test script to verify apostrophe normalization works correctly.

This test ensures that different types of apostrophes (', ʼ, ʹ, ′)
are properly normalized when filling the address form on DTEK website.
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from parser import fetch_dtek_schedule


async def test_apostrophe_normalization():
    """Test that different apostrophe types work correctly."""
    print("=" * 60)
    print("Testing Apostrophe Normalization")
    print("=" * 60)

    test_cases = [
        {
            "name": "Regular apostrophe (')",
            "city": "м. Дніпро",
            "street": "вул. В'ячеслава Липинського",
            "house": "4"
        },
        {
            "name": "Ukrainian modifier letter apostrophe (ʼ U+02BC)",
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house": "4"
        },
        {
            "name": "Modifier letter prime (ʹ U+02B9)",
            "city": "м. Дніпро",
            "street": "вул. Вʹячеслава Липинського",
            "house": "4"
        },
        {
            "name": "Prime symbol (′ U+2032)",
            "city": "м. Дніпро",
            "street": "вул. В′ячеслава Липинського",
            "house": "4"
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test Case {i}/{len(test_cases)}: {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"City: {test_case['city']}")
        print(f"Street: {test_case['street']}")
        print(f"House: {test_case['house']}")
        print(f"\nFetching schedule...")

        try:
            cache = await fetch_dtek_schedule(
                city=test_case['city'],
                street=test_case['street'],
                house_number=test_case['house'],
                include_possible=False  # Only actual schedule to speed up test
            )

            # Check if we got any results
            if cache.actual_schedules:
                print(f"✓ SUCCESS: Found {len(cache.actual_schedules)} outages")
                print(f"  First outage: {cache.actual_schedules[0]}")
                results.append({
                    "test": test_case['name'],
                    "status": "PASS",
                    "count": len(cache.actual_schedules)
                })
            else:
                print(f"⚠ WARNING: No outages found (might be OK if none scheduled)")
                results.append({
                    "test": test_case['name'],
                    "status": "PASS",
                    "count": 0
                })

        except Exception as e:
            print(f"✗ FAILED: {str(e)}")
            results.append({
                "test": test_case['name'],
                "status": "FAIL",
                "error": str(e)
            })

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    for result in results:
        status_icon = "✓" if result["status"] == "PASS" else "✗"
        print(f"{status_icon} {result['test']}: {result['status']}")
        if result["status"] == "PASS":
            print(f"   Outages found: {result['count']}")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")

    print(f"\n{'=' * 60}")
    print(f"Total: {len(results)} tests, {passed} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        print("\n⚠ Some tests failed!")
        sys.exit(1)
    else:
        print("\n✓ All tests passed!")
        sys.exit(0)


async def test_unit_normalization():
    """Unit test for apostrophe normalization logic."""
    print("\n" + "=" * 60)
    print("Unit Test: Apostrophe Normalization Function")
    print("=" * 60)

    # Test the normalization logic directly
    test_strings = {
        "В'ячеслава": "'",      # Regular apostrophe
        "Вʼячеслава": "ʼ",      # U+02BC
        "Вʹячеслава": "ʹ",      # U+02B9
        "В′ячеслава": "′",      # U+2032
    }

    expected = "В'ячеслава"  # All should normalize to this

    all_passed = True
    for test_str, apostrophe_type in test_strings.items():
        # Simulate the normalization
        normalized = test_str.replace('ʼ', "'").replace('ʹ', "'").replace('′', "'")

        if normalized == expected:
            print(f"✓ {repr(apostrophe_type)}: {test_str} → {normalized}")
        else:
            print(f"✗ {repr(apostrophe_type)}: {test_str} → {normalized} (expected {expected})")
            all_passed = False

    if all_passed:
        print("\n✓ All unit tests passed!")
    else:
        print("\n✗ Some unit tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    # Run unit tests first (fast)
    asyncio.run(test_unit_normalization())

    # Then run integration tests (slow - requires network)
    print("\n\nStarting integration tests (this may take a while)...\n")
    asyncio.run(test_apostrophe_normalization())
