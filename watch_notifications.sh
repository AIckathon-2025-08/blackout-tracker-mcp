#!/bin/bash
# Watch daemon logs and send macOS notifications
# Only sends ONE notification per outage (no repeats)

echo "👀 Watching for power outage notifications..."
echo "Press Ctrl+C to stop"
echo ""

# Track last notification time to avoid duplicates
last_notified=""

# Follow logs and look for notification messages
docker logs -f blackout-notifier 2>&1 | grep --line-buffered "Notification sent at" | while read line; do
    # Extract timestamp from "✓ Notification sent at HH:MM:SS"
    timestamp=$(echo "$line" | grep -oE "[0-9]{2}:[0-9]{2}:[0-9]{2}")

    # Only send if this is a new notification (different timestamp)
    if [ ! -z "$timestamp" ] && [ "$timestamp" != "$last_notified" ]; then
        last_notified="$timestamp"

        # Get the most recent outage info from logs
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
done
