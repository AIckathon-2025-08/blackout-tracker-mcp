"""
Test to verify that get_next_outage and check_upcoming_outages automatically
refresh stale cache data.

This test reproduces the bug scenario:
- Cache data is from Nov 21
- Current date is Nov 24
- Cache is more than 1 hour old (stale)
- Should automatically fetch fresh data instead of using stale cache
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from config import config, OutageSchedule, ScheduleType, ScheduleCache
from server import handle_get_next_outage, handle_set_address, handle_check_upcoming_outages, handle_configure_monitoring
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock


async def test_get_next_outage_auto_refresh_stale_cache():
    """Test that get_next_outage automatically refreshes stale cache."""
    print("=" * 60)
    print("Test: get_next_outage Auto-Refresh Stale Cache")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Кривий Ріг",
            "street": "вул. Вешенська",
            "house_number": "8"
        })

        # Create stale cache from 3 days ago
        old_date = datetime.now() - timedelta(days=3)
        old_date_str = old_date.strftime("%d.%m.%y")

        stale_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Old Day",
            date=old_date_str,
            start_hour=10,
            end_hour=12,
            outage_type="definite"
        )

        stale_cache = ScheduleCache(
            actual_schedules=[stale_outage],
            possible_schedules=[],
            last_updated=old_date  # 3 days old
        )
        config.save_schedule_cache(stale_cache)

        print(f"\nScenario:")
        print(f"  Current time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"  Cache age: {old_date.strftime('%Y-%m-%d %H:%M')} (3 days old)")
        print(f"  Cache should be refreshed (>1 hour old)")

        # Mock fetch_dtek_schedule to return fresh data
        fresh_date = datetime.now()
        fresh_date_str = fresh_date.strftime("%d.%m.%y")

        fresh_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Today",
            date=fresh_date_str,
            start_hour=14,
            end_hour=15,
            outage_type="definite"
        )

        fresh_cache = ScheduleCache(
            actual_schedules=[fresh_outage],
            possible_schedules=[],
            last_updated=fresh_date
        )

        # Mock the fetch function
        import server
        original_fetch = server.fetch_dtek_schedule

        async def mock_fetch(*args, **kwargs):
            print("  ✓ fetch_dtek_schedule was called (cache refreshed!)")
            return fresh_cache

        server.fetch_dtek_schedule = mock_fetch

        try:
            # Call get_next_outage - should trigger auto-refresh
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nResult:\n{result_text}")

            # Verify that fresh data is used (shows 14:00, not 10:00)
            has_fresh_data = "14:00" in result_text
            has_stale_data = "10:00" in result_text

            assert has_fresh_data, "Should show fresh data (14:00)"
            assert not has_stale_data, "Should NOT show stale data (10:00)"

            # Verify cache was updated
            updated_cache = config.load_schedule_cache()
            assert updated_cache.last_updated.date() == fresh_date.date(), "Cache should be updated"

            print(f"\n✓ Test PASSED - Stale cache was automatically refreshed")
            print(f"  Shows fresh data (14:00): {has_fresh_data}")
            print(f"  Shows stale data (10:00): {has_stale_data}")

            return True

        finally:
            server.fetch_dtek_schedule = original_fetch

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_check_upcoming_outages_auto_refresh():
    """Test that check_upcoming_outages also auto-refreshes stale cache."""
    print("\n" + "=" * 60)
    print("Test: check_upcoming_outages Auto-Refresh")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Кривий Ріг",
            "street": "вул. Вешенська",
            "house_number": "8"
        })

        # Enable monitoring
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 60
        })

        # Create stale cache
        old_date = datetime.now() - timedelta(hours=2)
        old_date_str = old_date.strftime("%d.%m.%y")

        stale_cache = ScheduleCache(
            actual_schedules=[],
            possible_schedules=[],
            last_updated=old_date
        )
        config.save_schedule_cache(stale_cache)

        print(f"\nScenario:")
        print(f"  Cache age: {old_date.strftime('%H:%M')} (2 hours old)")
        print(f"  Cache should be refreshed")

        # Mock fetch
        fresh_date = datetime.now()
        fresh_cache = ScheduleCache(
            actual_schedules=[],
            possible_schedules=[],
            last_updated=fresh_date
        )

        import server
        original_fetch = server.fetch_dtek_schedule

        fetch_called = False

        async def mock_fetch(*args, **kwargs):
            nonlocal fetch_called
            fetch_called = True
            print("  ✓ fetch_dtek_schedule was called for notifications")
            return fresh_cache

        server.fetch_dtek_schedule = mock_fetch

        try:
            # Call check_upcoming_outages - should trigger refresh
            result = await handle_check_upcoming_outages({})

            assert fetch_called, "fetch_dtek_schedule should have been called"

            print(f"\n✓ Test PASSED - check_upcoming_outages also auto-refreshes")

            return True

        finally:
            server.fetch_dtek_schedule = original_fetch

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING AUTO-REFRESH FOR STALE CACHE")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_get_next_outage_auto_refresh_stale_cache())
    results.append(await test_check_upcoming_outages_auto_refresh())

    # Summary
    print("\n" + "=" * 60)
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
