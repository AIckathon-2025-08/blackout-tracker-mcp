#!/usr/bin/env python3
"""
Background daemon for electricity outage notifications.

This daemon runs continuously in a Docker container and monitors
for upcoming outages. It sends notifications through multiple channels:
- Terminal notifications (escape sequences for iTerm2/Terminal.app)
- Shared log file for monitoring
- System notifications (when possible)

This daemon starts automatically with docker-compose up and runs in background.
"""
import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import signal

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config import config, ScheduleType, TrackedOutage
from i18n import get_i18n

# Global flag for graceful shutdown
running = True


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running
    print("\n🛑 Shutting down notification daemon...")
    running = False


def send_terminal_notification(title: str, message: str):
    """
    Send terminal notification using ANSI escape sequences.
    Works with iTerm2, Terminal.app, and most modern terminals.
    """
    # iTerm2 notification (https://iterm2.com/documentation-escape-codes.html)
    # Format: ESC ] 9 ; message BEL
    notification = f"\033]9;{title}: {message}\007"
    print(notification, flush=True)

    # Also print visible notification
    print(f"\n{'=' * 70}")
    print(f"🔔 {title}")
    print(f"{'=' * 70}")
    print(message)
    print(f"{'=' * 70}\n")


def write_notification_log(title: str, message: str, log_path: str = "/tmp/outage_notifications.log"):
    """Write notification to shared log file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "a") as f:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"[{timestamp}] {title}\n")
            f.write(f"{'-' * 80}\n")
            f.write(f"{message}\n")
            f.write(f"{'=' * 80}\n\n")
            f.flush()
    except Exception as e:
        print(f"⚠️  Could not write to log: {e}")


def check_upcoming_outages(notified_outages: set):
    """
    Check for upcoming outages and send notifications if needed.

    Args:
        notified_outages: Set of already notified outage identifiers (date + start_hour)

    Returns:
        True if notification was sent, False otherwise.
    """
    i18n = get_i18n()

    # Get monitoring config
    monitoring = config.get_monitoring()

    if not monitoring.enabled:
        return False

    # Check if address is configured
    address = config.get_address()
    if not address:
        return False

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return False

    # Find upcoming outages within notification window
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    today_date = now.strftime("%d.%m.%y")

    # Filter only actual schedules
    actual_schedules = [s for s in cached.actual_schedules
                       if s.schedule_type == ScheduleType.ACTUAL]

    # Find outages starting within notification window
    upcoming_outages = []
    for schedule in actual_schedules:
        # Only check today's outages
        if schedule.date != today_date:
            continue

        # Calculate time until outage starts
        time_until_outage_minutes = (schedule.start_hour - current_hour) * 60 - current_minute

        # Check if outage is within notification window
        if 0 <= time_until_outage_minutes <= monitoring.notification_before_minutes:
            upcoming_outages.append((schedule, time_until_outage_minutes))

    # If there are upcoming outages, send notification
    if upcoming_outages:
        # Get the closest outage
        closest_outage, minutes_until = min(upcoming_outages, key=lambda x: x[1])

        # Create unique identifier for this outage (date + start hour)
        outage_id = f"{closest_outage.date}_{closest_outage.start_hour:02d}"

        # Check if we've already notified about this outage
        if outage_id in notified_outages:
            # Already notified, skip
            return False

        # Mark this outage as notified
        notified_outages.add(outage_id)

        # Track this outage for restoration monitoring
        tracked_outage = TrackedOutage(
            date=closest_outage.date,
            start_hour=closest_outage.start_hour,
            end_hour=closest_outage.end_hour,
            notified_about_start=True,
            notified_about_change=False
        )
        config.update_monitoring(tracked_outage=tracked_outage)

        # Format notification
        time_str = f"{closest_outage.start_hour:02d}:00-{closest_outage.end_hour:02d}:00"
        outage_type = i18n.t(f"messages.outage_types.{closest_outage.outage_type}")

        title = "⚠️  UPCOMING POWER OUTAGE"
        message = (
            f"⏰ Outage in {int(minutes_until)} minutes!\n"
            f"🕐 Time: {time_str}\n"
            f"📍 Type: {outage_type}\n"
            f"🏠 Address: {address.to_string()}\n"
            f"\n💡 Prepare now: charge devices, save work!"
        )

        # Send notifications through all channels
        send_terminal_notification(title, message)
        write_notification_log(title, message)

        return True

    return False


def check_schedule_changes():
    """
    Check if the schedule has changed for the currently tracked outage.
    Specifically checks 10 minutes before power restoration if the restoration time changed.

    Returns:
        True if notification was sent, False otherwise.
    """
    monitoring = config.get_monitoring()

    if not monitoring.enabled or not monitoring.tracked_outage:
        return False

    # Get current time
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    today_date = now.strftime("%d.%m.%y")

    tracked = monitoring.tracked_outage

    # Only check for today's outages
    if tracked.date != today_date:
        return False

    # Calculate minutes until restoration
    minutes_until_restoration = (tracked.end_hour - current_hour) * 60 - current_minute

    # Check if we're within 10 minutes of restoration time
    if not (0 <= minutes_until_restoration <= 10):
        return False

    # If we already notified about schedule change for this outage, skip
    if tracked.notified_about_change:
        return False

    # Load current schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return False

    # Find the current outage in the schedule
    actual_schedules = [s for s in cached.actual_schedules
                       if s.schedule_type == ScheduleType.ACTUAL]

    current_outage = None
    for schedule in actual_schedules:
        if (schedule.date == today_date and
            schedule.start_hour == tracked.start_hour):
            current_outage = schedule
            break

    if not current_outage:
        # Outage no longer in schedule - it was cancelled!
        address = config.get_address()
        title = "✅ SCHEDULE CHANGED"
        message = (
            f"🎉 Good news! Power outage was cancelled!\n"
            f"⏰ Was scheduled: {tracked.start_hour:02d}:00-{tracked.end_hour:02d}:00\n"
            f"🏠 Address: {address.to_string() if address else 'N/A'}\n"
            f"\n💡 Power should be available now or soon!"
        )
        send_terminal_notification(title, message)
        write_notification_log(title, message)

        # Mark as notified
        tracked.notified_about_change = True
        config.update_monitoring(tracked_outage=tracked)
        return True

    # Check if restoration time changed
    if current_outage.end_hour != tracked.end_hour:
        address = config.get_address()
        old_time = f"{tracked.end_hour:02d}:00"
        new_time = f"{current_outage.end_hour:02d}:00"

        if current_outage.end_hour > tracked.end_hour:
            # Outage extended
            title = "⚠️ SCHEDULE CHANGED - OUTAGE EXTENDED"
            emoji = "😞"
            change_text = "extended"
        else:
            # Outage shortened
            title = "✅ SCHEDULE CHANGED - POWER RETURNS EARLIER"
            emoji = "🎉"
            change_text = "shortened"

        message = (
            f"{emoji} Power restoration time has changed!\n"
            f"⏰ Was scheduled to return: {old_time}\n"
            f"🔄 Now will return: {new_time}\n"
            f"📊 Outage was {change_text}\n"
            f"🏠 Address: {address.to_string() if address else 'N/A'}"
        )

        send_terminal_notification(title, message)
        write_notification_log(title, message)

        # Update tracked outage with new end time
        tracked.end_hour = current_outage.end_hour
        tracked.notified_about_change = True
        config.update_monitoring(tracked_outage=tracked)
        return True

    return False


def main():
    """Main daemon loop."""
    global running

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    print("=" * 80)
    print("🔔 ELECTRICITY OUTAGE NOTIFICATION DAEMON")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Wait a bit for config to be ready
    time.sleep(2)

    # Get initial monitoring config
    monitoring = config.get_monitoring()

    print("Configuration:")
    print(f"  • Monitoring: {'enabled ✓' if monitoring.enabled else 'disabled ✗'}")

    if monitoring.enabled:
        print(f"  • Notify: {monitoring.notification_before_minutes} minutes before outage")
        print(f"  • Check interval: {monitoring.check_interval_minutes} minutes")
    else:
        print("\n⚠️  Monitoring is currently disabled.")
        print("Enable it by telling Claude: 'Enable notifications 30 minutes before outages'")

    print()
    print("Daemon is running in background...")
    print("Logs: /tmp/outage_notifications.log")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()

    check_count = 0
    last_notification_time = None
    # Initialize last_check_time in the past to trigger first check immediately
    last_check_time = datetime.now() - timedelta(hours=2)
    last_known_config = {
        'enabled': monitoring.enabled,
        'notification_before_minutes': monitoring.notification_before_minutes,
        'check_interval_minutes': monitoring.check_interval_minutes
    }

    # Track which outages have been notified (to send only once per outage)
    notified_outages = set()

    # Config check interval (30 seconds) - separate from outage check interval
    CONFIG_CHECK_INTERVAL = 30

    while running:
        try:
            current_time = datetime.now()

            # Reload config each time (in case user updated it)
            config._load_config()  # Force reload from disk
            monitoring = config.get_monitoring()

            # Detect config changes
            current_config = {
                'enabled': monitoring.enabled,
                'notification_before_minutes': monitoring.notification_before_minutes,
                'check_interval_minutes': monitoring.check_interval_minutes
            }

            if current_config != last_known_config:
                print(f"\n{'=' * 80}")
                print(f"🔄 CONFIGURATION UPDATED at {current_time.strftime('%H:%M:%S')}")
                print(f"{'=' * 80}")
                print(f"  • Monitoring: {'enabled ✓' if monitoring.enabled else 'disabled ✗'}")
                if monitoring.enabled:
                    print(f"  • Notify: {monitoring.notification_before_minutes} minutes before outage")
                    print(f"  • Check interval: {monitoring.check_interval_minutes} minutes")
                print(f"{'=' * 80}\n")
                last_known_config = current_config

                # Clear notified outages when config changes (so user gets re-notified with new settings)
                notified_outages.clear()

                # Force immediate check after config change to avoid missing notifications
                if monitoring.enabled:
                    last_check_time = datetime.now() - timedelta(hours=2)

            # Check if it's time to check for outages
            # For accurate notifications, check frequently enough to catch the window
            if monitoring.notification_before_minutes < 60:
                # For short notification windows, check every 1-2 minutes for accuracy
                effective_check_interval = max(1, monitoring.notification_before_minutes // 15)
            else:
                # For long notification windows, use larger intervals
                effective_check_interval = min(
                    monitoring.check_interval_minutes,
                    max(5, monitoring.notification_before_minutes // 10)
                )

            minutes_since_last_check = (current_time - last_check_time).total_seconds() / 60
            should_check_outages = minutes_since_last_check >= effective_check_interval

            # Only check if monitoring is enabled and it's time
            if monitoring.enabled and should_check_outages:
                check_count += 1
                print(f"[{current_time.strftime('%H:%M:%S')}] Check #{check_count}: Looking for upcoming outages...")

                notification_sent = check_upcoming_outages(notified_outages)

                if notification_sent:
                    last_notification_time = current_time
                    print(f"✓ Notification sent at {current_time.strftime('%H:%M:%S')}")
                else:
                    print(f"✓ No upcoming outages in next {monitoring.notification_before_minutes} min")

                # Also check for schedule changes (10 min before restoration)
                schedule_change_sent = check_schedule_changes()
                if schedule_change_sent:
                    print(f"✓ Schedule change notification sent at {current_time.strftime('%H:%M:%S')}")

                last_check_time = current_time
                print(f"   Next check in {effective_check_interval} minutes\n")
            elif not monitoring.enabled and minutes_since_last_check >= 60:
                # Print reminder every hour when disabled
                print(f"[{current_time.strftime('%H:%M:%S')}] Monitoring disabled. Waiting...")
                last_check_time = current_time

            # Sleep for CONFIG_CHECK_INTERVAL seconds before checking config again
            time.sleep(CONFIG_CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n🛑 Received interrupt signal...")
            break
        except Exception as e:
            print(f"❌ Error in daemon loop: {e}")
            print(f"   Will retry in 60 seconds...")
            time.sleep(60)

    print("\n✓ Daemon stopped gracefully")
    print(f"Total checks performed: {check_count}")
    if last_notification_time:
        print(f"Last notification: {last_notification_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
