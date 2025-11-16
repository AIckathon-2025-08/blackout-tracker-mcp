#!/bin/bash
# Watch daemon logs and send macOS notifications
# Only sends ONE notification per outage (no repeats)

echo "👀 Watching for power outage notifications..."
echo "Press Ctrl+C to stop"
echo ""

# Send greeting notification to confirm system is working
echo "[$(date '+%H:%M:%S')] 👋 Sending greeting notification..."
terminal-notifier \
    -title "⚡ Notification System Active" \
    -subtitle "Blackout Tracker is watching for outages" \
    -message "✓ Your notifications are enabled
You'll be alerted before power outages" \
    -sound "Funk" \
    -group "blackout-system"

echo "✓ Greeting notification sent"
echo ""

# Track last notification time to avoid duplicates
last_notified=""

# Follow logs and look for notification messages
docker logs -f blackout-notifier 2>&1 | grep --line-buffered -E "(Notification sent at|Schedule change notification sent at)" | while read line; do
    # Extract timestamp from log line
    timestamp=$(echo "$line" | grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}")

    # Only send if this is a new notification (different timestamp)
    if [ ! -z "$timestamp" ] && [ "$timestamp" != "$last_notified" ]; then
        last_notified="$timestamp"

        # Check if this is a schedule change notification
        if echo "$line" | grep -q "Schedule change"; then
            # Get schedule change details from recent logs
            change_info=$(docker logs blackout-notifier --tail 30 | grep -A 5 "SCHEDULE CHANGED")

            if echo "$change_info" | grep -q "OUTAGE EXTENDED"; then
                # Outage extended
                old_time=$(echo "$change_info" | grep "Was scheduled to return" | grep -oE "[0-9]{2}:[0-9]{2}")
                new_time=$(echo "$change_info" | grep "Now will return" | grep -oE "[0-9]{2}:[0-9]{2}")

                echo "[$(date '+%H:%M:%S')] 🔔 Schedule change: outage extended to $new_time"

                terminal-notifier \
                    -title "⚠️ SCHEDULE CHANGED" \
                    -subtitle "Outage extended | Відключення подовжено" \
                    -message "Power will return at $new_time (was $old_time)
Світло повернеться о $new_time (було $old_time)" \
                    -sound "Basso" \
                    -group "schedule-change"

            elif echo "$change_info" | grep -q "POWER RETURNS EARLIER"; then
                # Outage shortened
                old_time=$(echo "$change_info" | grep "Was scheduled to return" | grep -oE "[0-9]{2}:[0-9]{2}")
                new_time=$(echo "$change_info" | grep "Now will return" | grep -oE "[0-9]{2}:[0-9]{2}")

                echo "[$(date '+%H:%M:%S')] 🔔 Schedule change: power returns earlier at $new_time"

                terminal-notifier \
                    -title "✅ GOOD NEWS!" \
                    -subtitle "Power returns earlier | Світло раніше" \
                    -message "Power will return at $new_time (was $old_time)
Світло повернеться о $new_time (було $old_time)" \
                    -sound "Glass" \
                    -group "schedule-change"

            elif echo "$change_info" | grep -q "cancelled"; then
                # Outage cancelled
                echo "[$(date '+%H:%M:%S')] 🔔 Schedule change: outage cancelled!"

                terminal-notifier \
                    -title "🎉 OUTAGE CANCELLED!" \
                    -subtitle "Power is available | Світло є" \
                    -message "Good news! The scheduled outage was cancelled.
Відключення скасовано!" \
                    -sound "Hero" \
                    -group "schedule-change"
            fi
        else
            # Regular outage warning notification
            outage_info=$(docker logs blackout-notifier --tail 20 | grep "Outage in" | tail -1)
            minutes=$(echo "$outage_info" | grep -oE "[0-9]+ minutes" | head -1 | grep -oE "[0-9]+")

            if [ ! -z "$minutes" ]; then
                echo "[$(date '+%H:%M:%S')] 🔔 Sending notification: $minutes minutes until outage"

                terminal-notifier \
                    -title "⚡ POWER OUTAGE | ВІДКЛЮЧЕННЯ СВІТЛА" \
                    -subtitle "In $minutes minutes | Через $minutes хвилин" \
                    -message "⏰ Prepare now: charge devices, save work!
⏰ Підготуйтеся: зарядіть пристрої, збережіть роботу!" \
                    -sound "Sosumi" \
                    -group "power-outage"
            fi
        fi
    fi
done
