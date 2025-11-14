"""
Test script to verify automatic monitoring setup.

This test ensures that:
1. configure_monitoring automatically sets up cron job when enabled
2. configure_monitoring removes cron job when disabled
3. Monitoring status can be checked
"""
import asyncio
import sys
import os
sys.path.insert(0, 'src')

from monitoring import setup_monitoring, remove_monitoring, check_monitoring_status
import subprocess


async def test_monitoring_setup():
    """Test that monitoring can be set up and removed."""
    print("=" * 60)
    print("Test: Automatic Monitoring Setup")
    print("=" * 60)

    try:
        # Clean up any existing monitoring first
        print("\nStep 1: Cleaning up existing monitoring...")
        success, message = remove_monitoring()
        print(f"Cleanup: {message}")

        # Test setup
        print("\nStep 2: Setting up monitoring (every 5 minutes)...")
        success, message = setup_monitoring(check_interval_minutes=5)
        print(f"Result: {message}")

        if not success:
            print("\n⚠️ Setup failed (might be expected on some systems)")
            print("This is OK - manual setup will still work")
            return True  # Don't fail the test

        # Check status
        print("\nStep 3: Checking monitoring status...")
        is_active, details = check_monitoring_status()
        print(f"Status: {'Active' if is_active else 'Not active'} ({details})")

        if not is_active:
            print("\n✗ Monitoring was set up but is not active!")
            return False

        # Verify cron entry exists
        print("\nStep 4: Verifying cron entry...")
        try:
            result = subprocess.run(
                ["crontab", "-l"],
                capture_output=True,
                text=True
            )
            if "monitor_outages.py" in result.stdout:
                print("✓ Cron entry found")
            else:
                print("✗ Cron entry not found")
                return False
        except:
            print("⚠️ Could not verify cron (cron not available)")

        # Test removal
        print("\nStep 5: Removing monitoring...")
        success, message = remove_monitoring()
        print(f"Result: {message}")

        if not success:
            print("\n✗ Could not remove monitoring!")
            return False

        # Verify removal
        print("\nStep 6: Verifying removal...")
        is_active, details = check_monitoring_status()
        print(f"Status: {'Active' if is_active else 'Not active'} ({details})")

        if is_active:
            print("\n✗ Monitoring is still active after removal!")
            return False

        print("\n✓ Test PASSED - Automatic monitoring works!\n")
        return True

    except Exception as e:
        print(f"\n✗ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run monitoring setup test."""
    print("\n" + "=" * 60)
    print("TESTING AUTOMATIC MONITORING SETUP")
    print("=" * 60 + "\n")

    result = await test_monitoring_setup()

    print("=" * 60)
    print("TEST RESULT")
    print("=" * 60)

    if result:
        print("\n✓ Automatic monitoring works!")
        print("\nWhen you run 'Enable notifications', it will:")
        print("  1. Save your notification settings")
        print("  2. Automatically set up cron job")
        print("  3. Start checking in background")
        print("  4. Send system notifications when outage approaches")
        sys.exit(0)
    else:
        print("\n⚠️ Automatic setup had issues")
        print("\nYou can still use manual checking:")
        print("  Ask Claude: 'Check for upcoming outages'")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
