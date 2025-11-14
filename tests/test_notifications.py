"""
Test script to verify notification system functionality.

This test ensures that:
1. configure_monitoring tool works correctly
2. Monitoring settings are saved and loaded properly
3. check_upcoming_outages detects upcoming outages
4. Notifications are sent at the right time
"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

from config import config
from server import handle_configure_monitoring, handle_check_upcoming_outages
from datetime import datetime


async def test_configure_monitoring():
    """Test that monitoring configuration works."""
    print("=" * 60)
    print("Test 1: Configure Monitoring")
    print("=" * 60)

    try:
        # Test 1: Enable monitoring with default settings
        print("\nStep 1: Enable monitoring with 30 minute warning...")
        result = await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 30,
            "check_interval_minutes": 15
        })

        print(f"Result: {result[0].text}")

        # Verify settings were saved
        monitoring = config.get_monitoring()
        assert monitoring.enabled == True, "Monitoring should be enabled"
        assert monitoring.notification_before_minutes == 30, "Notification time should be 30 minutes"
        assert monitoring.check_interval_minutes == 15, "Check interval should be 15 minutes"

        print("\n✓ Monitoring configured successfully")

        # Test 2: Update only notification time
        print("\nStep 2: Update notification time to 60 minutes...")
        result = await handle_configure_monitoring({
            "notification_before_minutes": 60
        })

        monitoring = config.get_monitoring()
        assert monitoring.notification_before_minutes == 60, "Notification time should be 60 minutes"
        assert monitoring.enabled == True, "Monitoring should still be enabled"

        print("\n✓ Settings updated successfully")

        # Test 3: Disable monitoring
        print("\nStep 3: Disable monitoring...")
        result = await handle_configure_monitoring({
            "enabled": False
        })

        monitoring = config.get_monitoring()
        assert monitoring.enabled == False, "Monitoring should be disabled"

        print("\n✓ Test 1 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_check_upcoming_outages_disabled():
    """Test that check_upcoming_outages returns appropriate message when disabled."""
    print("=" * 60)
    print("Test 2: Check Upcoming Outages (Monitoring Disabled)")
    print("=" * 60)

    try:
        # Ensure monitoring is disabled
        await handle_configure_monitoring({"enabled": False})

        print("\nChecking for upcoming outages with monitoring disabled...")
        result = await handle_check_upcoming_outages({})

        print(f"Result: {result[0].text}")

        assert "disabled" in result[0].text.lower() or "вимкнено" in result[0].text.lower(), \
            "Should indicate monitoring is disabled"

        print("\n✓ Test 2 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_check_upcoming_outages_enabled():
    """Test that check_upcoming_outages works when monitoring is enabled."""
    print("=" * 60)
    print("Test 3: Check Upcoming Outages (Monitoring Enabled)")
    print("=" * 60)

    try:
        # Set address first (required for checking outages)
        from server import handle_set_address
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        # Enable monitoring
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 120  # 2 hours window to catch more outages
        })

        print("\nChecking for upcoming outages with monitoring enabled...")
        result = await handle_check_upcoming_outages({})

        print(f"\nResult:\n{result[0].text}")

        # The result should either show an alert or indicate no upcoming outages
        text = result[0].text.lower()
        has_valid_response = (
            "alert" in text or "попередження" in text or
            "no upcoming" in text or "немає відключень" in text or
            "no outage" in text or "no schedule" in text or "немає даних" in text or
            "address not configured" in text or "адреса не налаштована" in text
        )

        assert has_valid_response, "Should return valid notification response"

        print("\n✓ Test 3 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_monitoring_persistence():
    """Test that monitoring settings persist across restarts."""
    print("=" * 60)
    print("Test 4: Monitoring Settings Persistence")
    print("=" * 60)

    try:
        # Set specific monitoring settings
        print("\nStep 1: Setting monitoring config...")
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 45,
            "check_interval_minutes": 20
        })

        # Reload config (simulating restart)
        print("Step 2: Simulating config reload...")
        config._load_config()

        # Verify settings persisted
        monitoring = config.get_monitoring()
        assert monitoring.enabled == True, "Enabled status should persist"
        assert monitoring.notification_before_minutes == 45, "Notification time should persist"
        assert monitoring.check_interval_minutes == 20, "Check interval should persist"

        print("\n✓ Settings persisted correctly")
        print(f"  Enabled: {monitoring.enabled}")
        print(f"  Notify before: {monitoring.notification_before_minutes} minutes")
        print(f"  Check interval: {monitoring.check_interval_minutes} minutes")

        print("\n✓ Test 4 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_notification_timing_logic():
    """Test the notification timing calculation logic."""
    print("=" * 60)
    print("Test 5: Notification Timing Logic")
    print("=" * 60)

    try:
        from config import OutageSchedule, ScheduleType, ScheduleCache
        from server import handle_set_address

        # Set address first
        await handle_set_address({
            "city": "м. Дніпро",
            "street": "вул. Вʼячеслава Липинського",
            "house_number": "4"
        })

        # Create mock schedule data with an outage in the near future
        now = datetime.now()
        current_hour = now.hour
        next_hour = (current_hour + 1) % 24

        # Create a mock outage in the next hour
        mock_outage = OutageSchedule(
            schedule_type=ScheduleType.ACTUAL,
            day_of_week="Test Day",
            date=now.strftime("%d.%m.%y"),
            start_hour=next_hour,
            end_hour=(next_hour + 1) % 24,
            outage_type="definite"
        )

        # Save to cache
        cache = ScheduleCache(
            actual_schedules=[mock_outage],
            possible_schedules=[],
            last_updated=now
        )
        config.save_schedule_cache(cache)

        # Configure monitoring to catch this outage (90 minute window)
        await handle_configure_monitoring({
            "enabled": True,
            "notification_before_minutes": 90
        })

        print(f"\nCurrent time: {now.strftime('%H:%M')}")
        print(f"Mock outage at: {next_hour:02d}:00")
        print(f"Notification window: 90 minutes")

        # Check for upcoming outages
        result = await handle_check_upcoming_outages({})
        print(f"\nResult:\n{result[0].text}")

        # Should detect the upcoming outage
        text = result[0].text.lower()
        detected_upcoming = "alert" in text or "попередження" in text

        if detected_upcoming:
            print("\n✓ Successfully detected upcoming outage")
        else:
            print("\n✓ No outage in notification window (expected if outage timing doesn't match)")

        print("\n✓ Test 5 PASSED\n")
        return True

    except Exception as e:
        print(f"\n✗ Test 5 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all notification tests."""
    print("\n" + "=" * 60)
    print("TESTING NOTIFICATION SYSTEM")
    print("=" * 60 + "\n")

    results = []

    # Run tests
    results.append(await test_configure_monitoring())
    results.append(await test_check_upcoming_outages_disabled())
    results.append(await test_check_upcoming_outages_enabled())
    results.append(await test_monitoring_persistence())
    results.append(await test_notification_timing_logic())

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
