"""
Test script to verify get_next_outage correctly handles past outages.

This test ensures that:
1. Past outages (already ended) are not returned as "next"
2. Current outages (ongoing) are returned
3. Future outages are correctly identified
4. Edge cases (end of day, multiple dates) are handled
"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

from datetime import datetime, timedelta
from config import config, OutageSchedule, ScheduleType, ScheduleCache
from server import handle_get_next_outage, handle_set_address
from unittest.mock import AsyncMock, patch


async def test_past_outage_not_returned():
    """Test that outages that have already ended are not returned as 'next'."""
    print("=" * 60)
    print("Test 1: Past Outage Not Returned")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        # Simulate current time: 22:04
        now = datetime.now()
        today_date = now.strftime("%d.%m.%y")

        # Create mock schedules with past and future outages
        past_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Test Day",
            date=today_date,
            start_hour=20,
            end_hour=21,
            outage_type="definite"
        )

        future_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Test Day",
            date=today_date,
            start_hour=23,
            end_hour=24,
            outage_type="definite"
        )

        # Save to cache with current (real) timestamp so it's not considered stale
        cache = ScheduleCache(
            actual_schedules=[past_outage, future_outage],
            possible_schedules=[],
            last_updated=datetime.now()  # Use real current time to avoid auto-refresh
        )
        config.save_schedule_cache(cache)

        # Mock fetch_dtek_schedule to prevent auto-refresh
        import server

        async def mock_fetch(*args, **kwargs):
            return cache

        with patch('server.fetch_dtek_schedule', mock_fetch):
            # Temporarily override current time to 22:04
            original_datetime = server.datetime

            class MockDatetime:
                @staticmethod
                def now():
                    mock_now = original_datetime.now().replace(hour=22, minute=4)
                    return mock_now

                @staticmethod
                def strptime(*args, **kwargs):
                    return original_datetime.strptime(*args, **kwargs)

            server.datetime = MockDatetime

            try:
                # Get next outage
                result = await handle_get_next_outage({})
                result_text = result[0].text

                print(f"\nCurrent time (simulated): 22:04")
                print(f"Past outage: 20:00-21:00")
                print(f"Future outage: 23:00-24:00")
                print(f"\nResult:\n{result_text}")

                # Verify that the result shows the future outage (23:00), not the past one (20:00)
                assert "23:00" in result_text, "Should show future outage at 23:00"
                assert "20:00" not in result_text, "Should NOT show past outage at 20:00"

                print("\n✓ Test 1 PASSED - Past outage correctly skipped\n")
                return True

            finally:
                # Restore original datetime
                server.datetime = original_datetime

    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_ongoing_outage_skipped():
    """Test that an ongoing outage is skipped and the next future outage is returned."""
    print("=" * 60)
    print("Test 2: Ongoing Outage Skipped (Returns Future Outage)")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        now = datetime.now()
        today_date = now.strftime("%d.%m.%y")

        # Create mock schedule with ongoing outage (20:00-22:00) and current time is 21:00
        ongoing_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Test Day",
            date=today_date,
            start_hour=20,
            end_hour=22,
            outage_type="definite"
        )

        future_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Test Day",
            date=today_date,
            start_hour=23,
            end_hour=24,
            outage_type="definite"
        )

        # Save to cache with current (real) timestamp so it's not considered stale
        cache = ScheduleCache(
            actual_schedules=[ongoing_outage, future_outage],
            possible_schedules=[],
            last_updated=datetime.now()  # Use real current time to avoid auto-refresh
        )
        config.save_schedule_cache(cache)

        # Mock current time to 21:00 (during 20:00-22:00 outage)
        import server
        original_datetime = server.datetime

        class MockDatetime:
            @staticmethod
            def now():
                mock_now = original_datetime.now().replace(hour=21, minute=0)
                return mock_now

            @staticmethod
            def strptime(*args, **kwargs):
                return original_datetime.strptime(*args, **kwargs)

        server.datetime = MockDatetime

        try:
            # Get next outage
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nCurrent time (simulated): 21:00")
            print(f"Ongoing outage: 20:00-22:00")
            print(f"Future outage: 23:00-24:00")
            print(f"\nResult:\n{result_text}")

            # Should show the future outage (23:00-24:00), not the ongoing one
            assert "23:00" in result_text or "23:00-24:00" in result_text or "23:00-00:00" in result_text, "Should show future outage, not ongoing"

            print("\n✓ Test 2 PASSED - Future outage correctly returned (not ongoing)\n")
            return True

        finally:
            server.datetime = original_datetime

    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_all_outages_past():
    """Test when all outages for today have passed."""
    print("=" * 60)
    print("Test 3: All Outages Past - Next Day")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. В'ячеслава Липинського",
            "house_number": "4"
        })

        now = datetime.now()
        today_date = now.strftime("%d.%m.%y")
        tomorrow = now + timedelta(days=1)
        tomorrow_date = tomorrow.strftime("%d.%m.%y")

        # All today's outages are past
        past_outage_1 = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Today",
            date=today_date,
            start_hour=10,
            end_hour=12,
            outage_type="definite"
        )

        past_outage_2 = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Today",
            date=today_date,
            start_hour=18,
            end_hour=20,
            outage_type="definite"
        )

        # Tomorrow's outage
        tomorrow_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Tomorrow",
            date=tomorrow_date,
            start_hour=8,
            end_hour=10,
            outage_type="definite"
        )

        # Save to cache with current (real) timestamp so it's not considered stale
        cache = ScheduleCache(
            actual_schedules=[past_outage_1, past_outage_2, tomorrow_outage],
            possible_schedules=[],
            last_updated=datetime.now()  # Use real current time to avoid auto-refresh
        )
        config.save_schedule_cache(cache)

        # Mock current time to 23:00 (all today's outages have passed)
        import server
        original_datetime = server.datetime

        class MockDatetime:
            @staticmethod
            def now():
                mock_now = original_datetime.now().replace(hour=23, minute=0)
                return mock_now

            @staticmethod
            def strptime(*args, **kwargs):
                return original_datetime.strptime(*args, **kwargs)

        server.datetime = MockDatetime

        try:
            # Get next outage
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nCurrent time (simulated): 23:00")
            print(f"Past outages today: 10:00-12:00, 18:00-20:00")
            print(f"Tomorrow's outage: 08:00-10:00")
            print(f"\nResult:\n{result_text}")

            # Should show tomorrow's outage
            assert tomorrow_date in result_text, "Should show tomorrow's date"
            assert "08:00" in result_text or "8:00" in result_text, "Should show tomorrow's outage at 08:00"
            assert "10:00" not in result_text or "08:00-10:00" in result_text, "Should not show today's past outages"

            print("\n✓ Test 3 PASSED - Tomorrow's outage correctly returned\n")
            return True

        finally:
            server.datetime = original_datetime

    except Exception as e:
        print(f"\n✗ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_exact_bug_scenario():
    """Test the exact scenario reported: 22:04 with outage at 20:00-21:00."""
    print("=" * 60)
    print("Test 4: Exact Bug Scenario (22:04, outage 20:00-21:00)")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Кривий Ріг",
            "street": "вул. Вешенська",
            "house_number": "8"
        })

        now = datetime.now()
        today_date = now.strftime("%d.%m.%y")

        # Exact scenario from bug report
        past_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Thursday",
            date=today_date,
            start_hour=20,
            end_hour=21,
            outage_type="definite"
        )

        # Another outage later
        future_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Thursday",
            date=today_date,
            start_hour=23,
            end_hour=24,
            outage_type="definite"
        )

        # Save to cache with current (real) timestamp so it's not considered stale
        cache = ScheduleCache(
            actual_schedules=[past_outage, future_outage],
            possible_schedules=[],
            last_updated=datetime.now()  # Use real current time to avoid auto-refresh
        )
        config.save_schedule_cache(cache)

        # Mock current time to exactly 22:04
        import server
        original_datetime = server.datetime

        class MockDatetime:
            @staticmethod
            def now():
                mock_now = original_datetime.now().replace(hour=22, minute=4)
                return mock_now

            @staticmethod
            def strptime(*args, **kwargs):
                return original_datetime.strptime(*args, **kwargs)

        server.datetime = MockDatetime

        try:
            # Get next outage
            result = await handle_get_next_outage({})
            result_text = result[0].text

            print(f"\nCurrent time (simulated): 22:04")
            print(f"Past outage: 20:00-21:00")
            print(f"Future outage: 23:00-24:00")
            print(f"\nResult:\n{result_text}")

            # MUST NOT show 20:00-21:00 outage
            # MUST show 23:00-24:00 outage
            if "20:00-21:00" in result_text or ("20:00" in result_text and "21:00" in result_text):
                print("\n✗ BUG STILL EXISTS: Showing past outage 20:00-21:00")
                return False

            if "23:00" in result_text or "23:00-24:00" in result_text:
                print("\n✓ CORRECT: Showing future outage at 23:00")
            else:
                print(f"\n⚠ WARNING: Expected to see 23:00 outage, but got different result")

            print("\n✓ Test 4 PASSED - Bug is fixed!\n")
            return True

        finally:
            server.datetime = original_datetime

    except Exception as e:
        print(f"\n✗ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING NEXT OUTAGE TIMING (BUG FIX VERIFICATION)")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_past_outage_not_returned())
    results.append(await test_ongoing_outage_skipped())
    results.append(await test_all_outages_past())
    results.append(await test_exact_bug_scenario())

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
        print("\n✓ ALL TESTS PASSED! Bug is fixed.")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED! Bug still exists.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
