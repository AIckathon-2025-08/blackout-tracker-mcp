"""
Battery information module for macOS.

Automatically retrieves battery status, capacity, and power consumption
from MacBook without requiring manual user input.

Supports two methods:
1. Bridge file (for Docker): reads /tmp/battery_status.json created by battery_info.sh
2. Direct system calls (for native macOS): uses pmset and ioreg commands
"""
import subprocess
import re
import logging
import json
import os
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

# Bridge file path (shared between host and Docker)
# Using /data path (mounted from project directory)
BATTERY_BRIDGE_FILE = "/data/battery_status.json"


class BatteryInfo:
    """Battery information for macOS devices."""

    def __init__(self):
        self.current_charge_percent: Optional[int] = None
        self.capacity_wh: Optional[float] = None
        self.is_charging: bool = False
        self.charging_power_w: Optional[float] = None
        self.discharge_rate_w: Optional[float] = None
        self.time_remaining_minutes: Optional[int] = None

    def __repr__(self):
        return (f"BatteryInfo(charge={self.current_charge_percent}%, "
                f"capacity={self.capacity_wh}Wh, charging={self.is_charging}, "
                f"power={self.charging_power_w or self.discharge_rate_w}W)")


def get_battery_info_from_bridge() -> Optional[BatteryInfo]:
    """
    Try to get battery info from bridge file (for Docker support).

    Returns:
        BatteryInfo object if bridge file exists and is valid, None otherwise
    """
    try:
        if not os.path.exists(BATTERY_BRIDGE_FILE):
            return None

        with open(BATTERY_BRIDGE_FILE, 'r') as f:
            data = json.load(f)

        # Check if data is recent (within last 60 seconds)
        import time
        age = time.time() - data.get('timestamp', 0)
        if age > 60:
            logger.warning(f"Battery bridge file is stale ({age:.0f}s old)")
            return None

        info = BatteryInfo()
        info.current_charge_percent = data.get('current_charge_percent')
        info.capacity_wh = data.get('capacity_wh')
        info.is_charging = data.get('is_charging', False)

        power_w = data.get('power_w', 0)
        if info.is_charging:
            info.charging_power_w = power_w
        else:
            info.discharge_rate_w = power_w

        logger.info(f"Battery info loaded from bridge file: {info}")
        return info

    except Exception as e:
        logger.debug(f"Could not read battery bridge file: {e}")
        return None


def get_battery_info_from_system() -> Optional[BatteryInfo]:
    """
    Get battery info directly from system (native macOS).

    Uses pmset and ioreg commands to retrieve:
    - Current charge percentage
    - Battery capacity in Wh
    - Charging status
    - Charging/discharge power

    Returns:
        BatteryInfo object with battery data, or None if unable to retrieve
    """
    try:
        info = BatteryInfo()

        # Get basic battery info using pmset
        pmset_output = subprocess.check_output(['pmset', '-g', 'batt'], text=True)

        # Parse charge percentage
        match = re.search(r'(\d+)%', pmset_output)
        if match:
            info.current_charge_percent = int(match.group(1))

        # Parse charging status
        info.is_charging = 'AC Power' in pmset_output or 'charging' in pmset_output.lower()

        # Get detailed battery info using ioreg
        ioreg_output = subprocess.check_output(
            ['ioreg', '-rn', 'AppleSmartBattery'],
            text=True
        )

        # Parse max capacity in mAh
        # Try AppleRawMaxCapacity first, then DesignCapacity, then MaxCapacity as fallback
        max_capacity_match = (
            re.search(r'"AppleRawMaxCapacity"\s*=\s*(\d+)', ioreg_output) or
            re.search(r'"DesignCapacity"\s*=\s*(\d+)', ioreg_output) or
            re.search(r'"MaxCapacity"\s*=\s*(\d+)', ioreg_output)
        )
        # Parse current capacity (mAh)
        current_capacity_match = (
            re.search(r'"AppleRawCurrentCapacity"\s*=\s*(\d+)', ioreg_output) or
            re.search(r'"CurrentCapacity"\s*=\s*(\d+)', ioreg_output)
        )
        # Parse voltage (mV)
        voltage_match = re.search(r'"Voltage"\s*=\s*(\d+)', ioreg_output)
        # Parse amperage (mA) - negative means discharging, positive means charging
        amperage_match = re.search(r'"Amperage"\s*=\s*(-?\d+)', ioreg_output)

        if max_capacity_match and voltage_match:
            max_capacity_mah = int(max_capacity_match.group(1))
            voltage_mv = int(voltage_match.group(1))

            # Calculate capacity in Wh: (mAh * V) / 1000
            info.capacity_wh = (max_capacity_mah * voltage_mv) / 1_000_000

            if amperage_match:
                amperage_ma = int(amperage_match.group(1))

                # Convert from unsigned to signed if needed (handle overflow)
                if amperage_ma > 2**63 - 1:
                    amperage_ma = amperage_ma - 2**64

                # Calculate power in W: (mA * mV) / 1_000_000
                power_w = abs((amperage_ma * voltage_mv) / 1_000_000)

                if amperage_ma > 0:
                    # Positive amperage = charging
                    info.is_charging = True
                    info.charging_power_w = power_w
                else:
                    # Negative amperage = discharging
                    info.discharge_rate_w = power_w

        # Estimate time remaining if discharging
        if not info.is_charging and current_capacity_match and info.discharge_rate_w:
            current_capacity_mah = int(current_capacity_match.group(1))
            if voltage_match and info.discharge_rate_w > 0:
                voltage_mv = int(voltage_match.group(1))
                # Current energy in Wh
                current_wh = (current_capacity_mah * voltage_mv) / 1_000_000
                # Time remaining in hours
                time_hours = current_wh / info.discharge_rate_w
                info.time_remaining_minutes = int(time_hours * 60)

        # Validate we have minimum required info
        if info.current_charge_percent is None or info.capacity_wh is None:
            logger.warning("Unable to retrieve complete battery information")
            return None

        logger.info(f"Battery info retrieved: {info}")
        return info

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to execute system command: {e}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving battery info from system: {e}", exc_info=True)
        return None


def get_battery_info() -> Optional[BatteryInfo]:
    """
    Get current battery information.

    Tries multiple methods in order:
    1. Bridge file (for Docker compatibility)
    2. Direct system calls (for native macOS)

    Returns:
        BatteryInfo object with battery data, or None if unable to retrieve
    """
    # Try bridge file first (Docker support)
    info = get_battery_info_from_bridge()
    if info:
        return info

    # Fall back to direct system calls (native macOS)
    info = get_battery_info_from_system()
    if info:
        return info

    logger.warning("Unable to retrieve battery information from any source")
    return None


def estimate_charging_power() -> float:
    """
    Estimate typical charging power for MacBook if not currently charging.

    Returns typical values based on common MacBook chargers:
    - MacBook Air: 30W
    - MacBook Pro 13": 61W
    - MacBook Pro 14"/16": 67-96W

    Default to conservative 65W.
    """
    # Could be enhanced to detect MacBook model and return appropriate value
    return 65.0


def get_default_target_percents() -> list[int]:
    """
    Get default target charge percentages.

    Returns:
        List of target percentages [80, 100]
        80% is recommended for battery health
        100% for maximum runtime
    """
    return [80, 100]
