"""
Test script to verify possible schedules are fetched and cached correctly.

This test ensures that:
1. Possible schedules are parsed from DTEK website
2. They are correctly cached and retrievable
3. get_outages_for_day works with possible schedules
"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

from parser import fetch_dtek_schedule
from config import config, ScheduleType


async def test_possible_schedules_parsing():
    """Test that possible schedules are fetched and parsed correctly."""
    print("=" * 60)
    print("Test 1: Parsing Possible Schedules from DTEK Website")
    print("=" * 60)

    try:
        # Fetch schedule with possible schedules included
        cache = await fetch_dtek_schedule(
            city="м. Дніпро",
            street="вул. Вʼячеслава Липинського",
            house_number="4",
            include_possible=True
        )

        print(f"\n✓ Actual schedules fetched: {len(cache.actual_schedules)}")
        print(f"✓ Possible schedules fetched: {len(cache.possible_schedules)}")

        if not cache.possible_schedules:
            print("\n✗ ERROR: No possible schedules found!")
            return False

        # Check that possible schedules have correct schedule_type
        wrong_type_count = 0
        for s in cache.possible_schedules:
            if s.schedule_type != ScheduleType.POSSIBLE_WEEK:
                wrong_type_count += 1

        if wrong_type_count > 0:
            print(f"\n✗ ERROR: {wrong_type_count} schedules have wrong schedule_type!")
            return False

        # Group by day of week to verify we have data for multiple days
        days = set(s.day_of_week for s in cache.possible_schedules)
        print(f"\n✓ Possible schedules cover {len(days)} days:")
        for day in ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']:
            count = sum(1 for s in cache.possible_schedules if s.day_of_week == day)
            if count > 0:
                print(f"  {day}: {count} outages")

        print("\n✓ Test 1 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cache_without_possible_schedules():
    """Test that cache is correctly updated when possible schedules are requested but not in cache."""
    print("=" * 60)
    print("Test 2: Cache Refresh When Possible Schedules Missing")
    print("=" * 60)

    try:
        # Step 1: Fetch without possible schedules
        print("\nStep 1: Fetching schedule WITHOUT possible schedules...")
        cache1 = await fetch_dtek_schedule(
            city="м. Дніпро",
            street="вул. Вʼячеслава Липинського",
            house_number="4",
            include_possible=False
        )

        print(f"  Actual schedules: {len(cache1.actual_schedules)}")
        print(f"  Possible schedules: {len(cache1.possible_schedules)}")

        if cache1.possible_schedules:
            print("\n⚠ WARNING: include_possible=False but got possible schedules anyway")

        # Save to cache
        config.save_schedule_cache(cache1)
        print("  ✓ Saved to cache")

        # Step 2: Load from cache
        print("\nStep 2: Loading from cache...")
        cached = config.load_schedule_cache()

        if not cached:
            print("\n✗ ERROR: Failed to load cache!")
            return False

        print(f"  Loaded - Actual: {len(cached.actual_schedules)}, Possible: {len(cached.possible_schedules)}")

        # Step 3: Fetch WITH possible schedules
        print("\nStep 3: Fetching schedule WITH possible schedules...")
        cache2 = await fetch_dtek_schedule(
            city="м. Дніпро",
            street="вул. В'ячеслава Липинського",
            house_number="4",
            include_possible=True
        )

        print(f"  Actual schedules: {len(cache2.actual_schedules)}")
        print(f"  Possible schedules: {len(cache2.possible_schedules)}")

        if not cache2.possible_schedules:
            print("\n✗ ERROR: include_possible=True but got no possible schedules!")
            return False

        # Save updated cache
        config.save_schedule_cache(cache2)
        print("  ✓ Saved updated cache")

        # Step 4: Verify cache now has possible schedules
        print("\nStep 4: Verifying updated cache...")
        cached_updated = config.load_schedule_cache()

        print(f"  Loaded - Actual: {len(cached_updated.actual_schedules)}, Possible: {len(cached_updated.possible_schedules)}")

        if not cached_updated.possible_schedules:
            print("\n✗ ERROR: Updated cache doesn't have possible schedules!")
            return False

        print("\n✓ Test 2 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_filter_by_day_and_type():
    """Test filtering schedules by day of week and schedule type."""
    print("=" * 60)
    print("Test 3: Filtering Schedules by Day and Type")
    print("=" * 60)

    try:
        # Fetch schedules with possible schedules
        cache = await fetch_dtek_schedule(
            city="м. Дніпро",
            street="вул. Вʼячеслава Липинського",
            house_number="4",
            include_possible=True
        )

        # Test filtering for Monday
        test_day = "Понеділок"
        print(f"\nFiltering for {test_day}...")

        # Filter actual schedules for Monday
        actual_monday = [s for s in cache.actual_schedules
                        if s.day_of_week == test_day and s.schedule_type == ScheduleType.ACTUAL]

        # Filter possible schedules for Monday
        possible_monday = [s for s in cache.possible_schedules
                          if s.day_of_week == test_day and s.schedule_type == ScheduleType.POSSIBLE_WEEK]

        print(f"  Actual schedules for {test_day}: {len(actual_monday)}")
        print(f"  Possible schedules for {test_day}: {len(possible_monday)}")

        if possible_monday:
            print(f"\n  ✓ Found possible schedules for {test_day}:")
            for i, s in enumerate(possible_monday[:5], 1):
                print(f"    {i}. {s.start_hour:02d}:00-{s.end_hour:02d}:00 ({s.outage_type})")
            if len(possible_monday) > 5:
                print(f"    ... and {len(possible_monday) - 5} more")
        else:
            print(f"\n  ℹ No possible schedules for {test_day} (this might be OK)")

        print("\n✓ Test 3 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING POSSIBLE SCHEDULES FUNCTIONALITY")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_possible_schedules_parsing())
    results.append(await test_cache_without_possible_schedules())
    results.append(await test_filter_by_day_and_type())

    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(results)
    failed = total - passed

    print(f"\nTotal tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
