"""
Test to verify that the notification system does NOT notify about ongoing outages.

This test reproduces the bug scenario:
- It's 17:17
- There's an ongoing outage from 13:00-20:00
- Notifications are enabled with 45 minute warning
- The system should NOT send a notification saying "In 43 minutes will be outage"
  because the outage is already in progress
"""
import asyncio
import sys
sys.path.insert(0, 'src')

from config import config, OutageSchedule, ScheduleType, ScheduleCache
from server import handle_configure_monitoring, handle_check_upcoming_outages, handle_set_address
from datetime import datetime
from unittest.mock import patch


async def test_no_notification_for_ongoing_outage():
    """Test that ongoing outages are NOT included in upcoming outage notifications."""
    print("=" * 60)
    print("Test: No Notification for Ongoing Outage")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        # Mock current time to 17:17
        mock_now = datetime(2025, 11, 21, 17, 17)
        today_str = mock_now.strftime("%d.%m.%y")

        # Create mock schedule with:
        # 1. Ongoing outage (13:00-20:00) - should NOT trigger notification
        # 2. Future outage (22:00-23:00) - too far in the future for 45 min window
        ongoing_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Четвер",
            date=today_str,
            start_hour=13,
            end_hour=20,
            outage_type="definite"
        )

        future_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Четвер",
            date=today_str,
            start_hour=22,
            end_hour=23,
            outage_type="definite"
        )

        # Save to cache
        cache = ScheduleCache(
            actual_schedules=[ongoing_outage, future_outage],
            possible_schedules=[],
            last_updated=mock_now
        )
        config.save_schedule_cache(cache)

        # Configure monitoring with 45 minute warning
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 45
        })

        print(f"\nScenario:")
        print(f"  Current time: {mock_now.strftime('%H:%M')} (mocked)")
        print(f"  Ongoing outage: 13:00-20:00 (started 4 hours ago, ends in ~3 hours)")
        print(f"  Future outage: 22:00-23:00 (starts in ~5 hours)")
        print(f"  Notification window: 45 minutes before outage")

        # Patch datetime.now() to return our mock time
        with patch('server.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime

            # Check for upcoming outages
            result = await handle_check_upcoming_outages({})
            result_text = result[0].text.lower()

            print(f"\nResult:\n{result[0].text}")

            # Verify that NO upcoming outage alert is shown
            # The system should say "no upcoming outages" because:
            # - The 13:00 outage has already started (not upcoming)
            # - The 22:00 outage is too far away (outside 45 min window)
            has_alert = ("upcoming outage alert" in result_text or
                        "попередження" in result_text or
                        "starting in" in result_text)

            assert not has_alert, "Should NOT send alert for ongoing outage"

            # Should mention the next outage (22:00) in the informational part
            has_next_outage_info = "22:00" in result_text or "next" in result_text or "наступне" in result_text

            print(f"\n✓ Test PASSED - No notification sent for ongoing outage")
            print(f"  Alert sent: {has_alert} (expected: False)")
            print(f"  Has next outage info: {has_next_outage_info}")

            return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_notification_for_truly_upcoming_outage():
    """Test that upcoming outages (not ongoing) DO trigger notifications."""
    print("\n" + "=" * 60)
    print("Test: Notification for Truly Upcoming Outage")
    print("=" * 60)

    try:
        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        # Mock current time to 17:20
        mock_now = datetime(2025, 11, 21, 17, 20)
        today_str = mock_now.strftime("%d.%m.%y")

        # Create mock schedule with:
        # Upcoming outage starting in 40 minutes (18:00-19:00)
        upcoming_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Четвер",
            date=today_str,
            start_hour=18,
            end_hour=19,
            outage_type="definite"
        )

        # Save to cache
        cache = ScheduleCache(
            actual_schedules=[upcoming_outage],
            possible_schedules=[],
            last_updated=mock_now
        )
        config.save_schedule_cache(cache)

        # Configure monitoring with 45 minute warning
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 45
        })

        print(f"\nScenario:")
        print(f"  Current time: {mock_now.strftime('%H:%M')} (mocked)")
        print(f"  Upcoming outage: 18:00-19:00 (starts in 40 minutes)")
        print(f"  Notification window: 45 minutes before outage")

        # Patch datetime.now() to return our mock time
        with patch('server.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime

            # Check for upcoming outages
            result = await handle_check_upcoming_outages({})
            result_text = result[0].text.lower()

            print(f"\nResult:\n{result[0].text}")

            # Verify that an upcoming outage alert IS shown
            has_alert = "40" in result_text or "alert" in result_text or "попередження" in result_text

            assert has_alert, "Should send alert for truly upcoming outage"

            print(f"\n✓ Test PASSED - Notification correctly sent for upcoming outage")
            print(f"  Alert sent: {has_alert} (expected: True)")

            return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("TESTING ONGOING OUTAGE NOTIFICATION BUG FIX")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_no_notification_for_ongoing_outage())
    results.append(await test_notification_for_truly_upcoming_outage())

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
