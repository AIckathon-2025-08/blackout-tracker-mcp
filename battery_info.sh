#!/bin/bash

# Battery Info Bridge Script for Docker
# Collects battery information from macOS and makes it available to Docker container
# Similar to watch_notifications.sh approach

BATTERY_FILE="/Users/Yaroslav_Yenkala/projects/epam/aickathon/electricity_shutdowns_mcp/battery_status.json"
UPDATE_INTERVAL=10  # seconds

echo "🔋 Battery Info Bridge started"
echo "   Updating battery status every ${UPDATE_INTERVAL}s"
echo "   Output: ${BATTERY_FILE}"
echo ""

update_battery_info() {
    # Get battery percentage
    BATTERY_PERCENT=$(pmset -g batt | grep -Eo "\d+%" | grep -Eo "\d+" | head -1)

    # Get detailed battery info
    IOREG_OUTPUT=$(ioreg -rn AppleSmartBattery)

    # Parse capacity (look for standalone property with " = " pattern)
    # This avoids matching nested BatteryData values
    # Using [0-9]+ instead of \d+ for POSIX compatibility
    CAPACITY_MAH=$(echo "$IOREG_OUTPUT" | grep -E '^\s+"(AppleRawMaxCapacity|DesignCapacity)"\s+=\s+[0-9]+' | grep -Eo "[0-9]+" | head -1)

    # If not found, try without leading spaces
    if [ -z "$CAPACITY_MAH" ]; then
        CAPACITY_MAH=$(echo "$IOREG_OUTPUT" | grep -E '"DesignCapacity"\s+=\s+[0-9]+$' | grep -Eo "[0-9]+" | head -1)
    fi

    # Parse voltage (mV) - match standalone property only
    VOLTAGE=$(echo "$IOREG_OUTPUT" | grep -E '^\s+"Voltage"\s+=\s+[0-9]+' | grep -Eo "[0-9]+" | head -1)

    # Parse amperage (mA) - match standalone property, can be negative for discharging
    AMPERAGE_RAW=$(echo "$IOREG_OUTPUT" | grep -E '^\s+"Amperage"\s+=\s+[0-9]+' | grep -Eo "[0-9]+" | head -1)

    # Convert unsigned to signed (handle overflow)
    # If amperage > 2^63-1, it's actually a negative number
    if [ ! -z "$AMPERAGE_RAW" ]; then
        # Use bc for large number comparison (bash can't handle numbers > 2^63)
        IS_NEGATIVE=$(echo "$AMPERAGE_RAW > 9223372036854775807" | bc)
        if [ "$IS_NEGATIVE" -eq 1 ]; then
            # Convert: subtract 2^64 to get signed value
            AMPERAGE=$(echo "$AMPERAGE_RAW - 18446744073709551616" | bc)
        else
            AMPERAGE=$AMPERAGE_RAW
        fi
    else
        AMPERAGE="0"
    fi

    # Check if charging (AC Power in pmset output)
    if pmset -g batt | grep -q "AC Power"; then
        IS_CHARGING="true"
    else
        IS_CHARGING="false"
    fi

    # Calculate capacity in Wh: (mAh * mV) / 1,000,000
    if [ ! -z "$CAPACITY_MAH" ] && [ ! -z "$VOLTAGE" ]; then
        CAPACITY_WH=$(echo "scale=2; ($CAPACITY_MAH * $VOLTAGE) / 1000000" | bc)
    else
        CAPACITY_WH="0"
    fi

    # Calculate power (W): abs(mA * mV) / 1,000,000
    if [ ! -z "$AMPERAGE" ] && [ ! -z "$VOLTAGE" ]; then
        # Get absolute value for power calculation
        if [ "$AMPERAGE" -lt 0 ]; then
            ABS_AMPERAGE=$(echo "$AMPERAGE * -1" | bc)
        else
            ABS_AMPERAGE=$AMPERAGE
        fi
        POWER_W=$(echo "scale=2; ($ABS_AMPERAGE * $VOLTAGE) / 1000000" | bc)
    else
        POWER_W="0"
    fi

    # Create JSON file
    cat > "$BATTERY_FILE" << EOF
{
    "current_charge_percent": ${BATTERY_PERCENT:-0},
    "capacity_wh": ${CAPACITY_WH:-0},
    "is_charging": ${IS_CHARGING:-false},
    "power_w": ${POWER_W:-0},
    "voltage_mv": ${VOLTAGE:-0},
    "amperage_ma": ${AMPERAGE:-0},
    "timestamp": $(date +%s)
}
EOF

    # Optional: print status every update
    # echo "[$(date '+%H:%M:%S')] Battery: ${BATTERY_PERCENT}%, Capacity: ${CAPACITY_WH}Wh, Power: ${POWER_W}W, Charging: ${IS_CHARGING}"
}

# Create initial battery info
update_battery_info

# Continuous update loop
while true; do
    sleep $UPDATE_INTERVAL
    update_battery_info
done
