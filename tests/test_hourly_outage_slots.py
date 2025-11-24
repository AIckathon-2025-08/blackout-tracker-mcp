"""
Test to verify that get_next_outage correctly handles hourly outage slots.

This test reproduces the real-world bug scenario:
- It's 18:11
- There's a continuous outage from 13:00-20:00 split into hourly slots:
  13:00-14:00, 14:00-15:00, ..., 18:00-19:00, 19:00-20:00
- Currently in the 18:00-19:00 slot
- Should return the outage AFTER 20:00, not 19:00-20:00 (which is part of the ongoing outage)
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from config import config, OutageSchedule, ScheduleType, ScheduleCache
from server import handle_get_next_outage, handle_set_address
from datetime import datetime
from unittest.mock import patch


async def test_hourly_slots_skip_ongoing():
    """Test that hourly outage slots are correctly handled when inside an ongoing outage."""
    print("=" * 60)
    print("Test: Hourly Outage Slots - Skip Ongoing")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Кривий Ріг",
            "street": "вул. Вешенська",
            "house_number": "8"
        })

        # Mock current time to 18:11
        mock_now = datetime(2025, 11, 21, 18, 11)
        today_str = mock_now.strftime("%d.%m.%y")

        # Create hourly outage slots from 13:00-20:00
        outage_slots = []
        for hour in range(13, 20):
            outage_slots.append(OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week="П'ятниця",
                date=today_str,
                start_hour=hour,
                end_hour=hour + 1,
                outage_type="definite"
            ))

        # Add a future outage after the continuous block
        future_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="П'ятниця",
            date=today_str,
            start_hour=23,
            end_hour=24,
            outage_type="definite"
        )

        outage_slots.append(future_outage)

        # Save to cache
        cache = ScheduleCache(
            actual_schedules=outage_slots,
            possible_schedules=[],
            last_updated=mock_now
        )
        config.save_schedule_cache(cache)

        print(f"\nScenario:")
        print(f"  Current time: {mock_now.strftime('%H:%M')} (mocked)")
        print(f"  Continuous outage: 13:00-20:00 (split into hourly slots)")
        print(f"  Current slot: 18:00-19:00 (ongoing)")
        print(f"  Next slot in same outage: 19:00-20:00")
        print(f"  Future outage after gap: 23:00-24:00")

        # Patch datetime.now() to return our mock time
        with patch('server.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime

            # Get next outage
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nResult:\n{result_text}")

            # Verify that it shows 23:00-24:00, NOT 19:00-20:00
            has_correct_outage = "23:00" in result_text
            has_wrong_outage = "19:00" in result_text

            assert has_correct_outage, "Should show 23:00 outage (the truly next one)"
            assert not has_wrong_outage, "Should NOT show 19:00 outage (part of ongoing outage)"

            print(f"\n✓ Test PASSED - Correctly skipped remaining slots of ongoing outage")
            print(f"  Shows 23:00 outage: {has_correct_outage} (expected: True)")
            print(f"  Shows 19:00 outage: {has_wrong_outage} (expected: False)")

            return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_hourly_slots_between_outages():
    """Test that hourly slots work correctly when NOT in an ongoing outage."""
    print("\n" + "=" * 60)
    print("Test: Hourly Slots - Between Outages")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Кривий Ріг",
            "street": "вул. Вешенська",
            "house_number": "8"
        })

        # Mock current time to 15:30 (between outages)
        mock_now = datetime(2025, 11, 21, 15, 30)
        today_str = mock_now.strftime("%d.%m.%y")

        # Create outage slots: 10:00-13:00 and 18:00-20:00
        outage_slots = []
        for hour in range(10, 13):
            outage_slots.append(OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week="П'ятниця",
                date=today_str,
                start_hour=hour,
                end_hour=hour + 1,
                outage_type="definite"
            ))

        for hour in range(18, 20):
            outage_slots.append(OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week="П'ятниця",
                date=today_str,
                start_hour=hour,
                end_hour=hour + 1,
                outage_type="definite"
            ))

        # Save to cache
        cache = ScheduleCache(
            actual_schedules=outage_slots,
            possible_schedules=[],
            last_updated=mock_now
        )
        config.save_schedule_cache(cache)

        print(f"\nScenario:")
        print(f"  Current time: {mock_now.strftime('%H:%M')} (mocked)")
        print(f"  Past outage: 10:00-13:00")
        print(f"  Current: Electricity ON")
        print(f"  Next outage: 18:00-20:00")

        # Patch datetime.now() to return our mock time
        with patch('server.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime

            # Get next outage
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nResult:\n{result_text}")

            # Verify that it shows 18:00
            has_correct_outage = "18:00" in result_text

            assert has_correct_outage, "Should show 18:00 outage (next one)"

            print(f"\n✓ Test PASSED - Correctly shows next outage block")

            return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING HOURLY OUTAGE SLOTS BUG FIX")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_hourly_slots_skip_ongoing())
    results.append(await test_hourly_slots_between_outages())

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
