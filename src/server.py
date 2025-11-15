"""
MCP Server for Electricity Shutdowns monitoring.

This server provides tools to check electricity outage schedules in Ukraine (DTEK).
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

from config import config, ScheduleType
from parser import fetch_dtek_schedule
from i18n import get_i18n
from monitoring import setup_monitoring, remove_monitoring, check_monitoring_status
from battery import get_battery_info, estimate_charging_power, get_default_target_percents


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Create MCP server instance
app = Server("blackout-tracker-mcp")

# Get i18n instance
i18n = get_i18n()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="check_outage_schedule",
            description=i18n.t("tool_descriptions.check_outage_schedule"),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_possible": {
                        "type": "boolean",
                        "description": i18n.t("tool_params.include_possible"),
                        "default": False
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": i18n.t("tool_params.force_refresh"),
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_next_outage",
            description=i18n.t("tool_descriptions.get_next_outage"),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_outages_for_day",
            description=i18n.t("tool_descriptions.get_outages_for_day"),
            inputSchema={
                "type": "object",
                "properties": {
                    "day_of_week": {
                        "type": "string",
                        "description": i18n.t("tool_params.day_of_week")
                    },
                    "schedule_type": {
                        "type": "string",
                        "enum": ["actual", "possible_week"],
                        "description": i18n.t("tool_params.schedule_type"),
                        "default": "actual"
                    }
                },
                "required": ["day_of_week"]
            }
        ),
        Tool(
            name="set_address",
            description=i18n.t("tool_descriptions.set_address"),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": i18n.t("tool_params.city")
                    },
                    "street": {
                        "type": "string",
                        "description": i18n.t("tool_params.street")
                    },
                    "house_number": {
                        "type": "string",
                        "description": i18n.t("tool_params.house_number")
                    }
                },
                "required": ["city", "street", "house_number"]
            }
        ),
        Tool(
            name="configure_monitoring",
            description=i18n.t("tool_descriptions.configure_monitoring"),
            inputSchema={
                "type": "object",
                "properties": {
                    "notification_before_minutes": {
                        "type": "integer",
                        "description": i18n.t("tool_params.notification_before_minutes"),
                        "default": 60
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": i18n.t("tool_params.enabled"),
                        "default": False
                    },
                    "check_interval_minutes": {
                        "type": "integer",
                        "description": i18n.t("tool_params.check_interval_minutes"),
                        "default": 60
                    }
                }
            }
        ),
        Tool(
            name="check_upcoming_outages",
            description=i18n.t("tool_descriptions.check_upcoming_outages"),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="calculate_charging_time",
            description=i18n.t("tool_descriptions.calculate_charging_time"),
            inputSchema={
                "type": "object",
                "properties": {
                    "target_charge_percent": {
                        "type": "integer",
                        "description": i18n.t("tool_params.target_charge_percent_optional")
                    }
                },
                "required": []
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "set_address":
            return await handle_set_address(arguments)
        elif name == "check_outage_schedule":
            return await handle_check_schedule(arguments)
        elif name == "get_next_outage":
            return await handle_get_next_outage(arguments)
        elif name == "get_outages_for_day":
            return await handle_get_outages_for_day(arguments)
        elif name == "configure_monitoring":
            return await handle_configure_monitoring(arguments)
        elif name == "check_upcoming_outages":
            return await handle_check_upcoming_outages(arguments)
        elif name == "calculate_charging_time":
            return await handle_calculate_charging_time(arguments)
        else:
            return [TextContent(type="text", text=f"Невідомий інструмент: {name}")]
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Помилка виконання: {str(e)}")]


async def handle_set_address(arguments: dict) -> list[TextContent]:
    """Handle set_address tool."""
    city = arguments.get("city", "").strip()
    street = arguments.get("street", "").strip()
    house_number = arguments.get("house_number", "").strip()

    if not city or not street or not house_number:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_missing")
        )]

    # Save address to config
    config.set_address(city=city, street=street, house_number=house_number)

    address_str = f"{city}, {street}, буд. {house_number}"
    return [TextContent(
        type="text",
        text=i18n.t("messages.address_saved", address=address_str)
    )]


async def handle_check_schedule(arguments: dict) -> list[TextContent]:
    """Handle check_outage_schedule tool."""
    include_possible = arguments.get("include_possible", False)
    force_refresh = arguments.get("force_refresh", False)

    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_not_configured")
        )]

    # Try to use cache if not forcing refresh
    if not force_refresh:
        cached = config.load_schedule_cache()
        if cached and cached.actual_schedules:
            # Check if cache is fresh (less than 1 hour old)
            cache_age = datetime.now() - cached.last_updated
            if cache_age.total_seconds() < 3600:  # 1 hour
                return [TextContent(
                    type="text",
                    text=format_schedule_response(cached, address, include_possible, from_cache=True)
                )]

    # Fetch fresh data - ALWAYS fetch both schedules since DTEK website always returns both
    logger.info(f"Fetching schedule for {address.to_string()}")
    try:
        schedule_cache = await fetch_dtek_schedule(
            city=address.city,
            street=address.street,
            house_number=address.house_number,
            include_possible=True  # Always fetch both schedules
        )

        # Save to cache
        config.save_schedule_cache(schedule_cache)

        return [TextContent(
            type="text",
            text=format_schedule_response(schedule_cache, address, include_possible, from_cache=False)
        )]

    except Exception as e:
        logger.error(f"Error fetching schedule: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=i18n.t("messages.error_fetching", error=str(e))
        )]


async def handle_get_next_outage(arguments: dict) -> list[TextContent]:
    """Handle get_next_outage tool."""
    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_not_configured")
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_schedule_data")
        )]

    # Find next outage
    now = datetime.now()
    current_hour = now.hour
    today_date = now.strftime("%d.%m.%y")

    # Filter only actual schedules and sort by date and hour
    actual_schedules = [s for s in cached.actual_schedules if s.schedule_type == ScheduleType.ACTUAL]

    # Find next outage (future only, not ongoing or past)
    # An outage is considered "next" if it hasn't started yet
    next_outage = None
    for schedule in actual_schedules:
        # Check if this is today's schedule
        if schedule.date == today_date:
            # For today, only consider outages that haven't started yet
            if schedule.start_hour > current_hour:
                next_outage = schedule
                break
        else:
            # For future dates (tomorrow), take the first one
            next_outage = schedule
            break

    if not next_outage and actual_schedules:
        # If no outage today and no future dates found, this shouldn't happen
        # but take first schedule as fallback
        next_outage = actual_schedules[0]

    if not next_outage:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_next_outage")
        )]

    # Format response
    time_str = f"{next_outage.start_hour:02d}:00-{next_outage.end_hour:02d}:00"
    date_str = f"{next_outage.date} " if next_outage.date else ""

    outage_type_desc = i18n.t(f"messages.outage_types.{next_outage.outage_type}")

    return [TextContent(
        type="text",
        text=f"{i18n.t('schedule.address_label')} {address.to_string()}\n\n"
             f"{i18n.t('schedule.next_outage_title')}\n"
             f"  {date_str}{next_outage.day_of_week}, {time_str}\n"
             f"  {i18n.t('schedule.type_label')} {outage_type_desc}\n\n"
             f"{i18n.t('schedule.data_updated')} {cached.last_updated.strftime('%d.%m.%Y %H:%M')}"
    )]


async def handle_get_outages_for_day(arguments: dict) -> list[TextContent]:
    """Handle get_outages_for_day tool."""
    day_of_week = arguments.get("day_of_week", "").strip()
    schedule_type = arguments.get("schedule_type", "actual")

    if not day_of_week:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_missing")  # Re-use, close enough
        )]

    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_not_configured")
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_schedule_data")
        )]

    # Filter schedules by day and type
    if schedule_type == ScheduleType.ACTUAL:
        schedules = [s for s in cached.actual_schedules
                    if s.day_of_week == day_of_week and s.schedule_type == ScheduleType.ACTUAL]
        schedule_type_label = i18n.t("schedule.schedule_type_actual")
    else:
        schedules = [s for s in cached.possible_schedules
                    if s.day_of_week == day_of_week and s.schedule_type == ScheduleType.POSSIBLE_WEEK]
        schedule_type_label = i18n.t("schedule.schedule_type_possible")

    if not schedules:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_outages_for_day", day=day_of_week, schedule_type=schedule_type_label)
        )]

    # Format response
    result = f"{i18n.t('schedule.address_label')} {address.to_string()}\n"
    result += f"{i18n.t('schedule.day_label')} {day_of_week}\n"
    result += f"{i18n.t('schedule.schedule_type_label')} {schedule_type_label}\n\n"
    result += i18n.t("schedule.outages_count", count=len(schedules)) + "\n"

    for schedule in schedules:
        time_str = f"{schedule.start_hour:02d}:00-{schedule.end_hour:02d}:00"
        date_str = f"{schedule.date} " if schedule.date else ""

        outage_type_desc = {
            "definite": "✗",
            "first_30min": "⚡",
            "second_30min": "⚡*",
            "possible": "~"
        }.get(schedule.outage_type, "?")

        result += f"  {outage_type_desc} {date_str}{time_str} ({schedule.outage_type})\n"

    result += f"\n{i18n.t('schedule.data_updated')} {cached.last_updated.strftime('%d.%m.%Y %H:%M')}"

    return [TextContent(type="text", text=result)]


def format_schedule_response(
    schedule_cache,
    address,
    include_possible: bool,
    from_cache: bool
) -> str:
    """Format schedule data into readable response."""
    source = i18n.t('schedule.source_cache') if from_cache else i18n.t('schedule.source_fresh')
    result = f"{i18n.t('schedule.address_label')} {address.to_string()}\n"
    result += f"{i18n.t('schedule.source_label')} {source}\n"
    result += f"{i18n.t('schedule.updated_label')} {schedule_cache.last_updated.strftime('%d.%m.%Y %H:%M')}\n\n"

    # Actual schedule
    result += "=" * 50 + "\n"
    result += f"📊 {i18n.t('schedule.actual_title')}\n"
    result += "=" * 50 + "\n\n"

    if schedule_cache.actual_schedules:
        result += f"{i18n.t('schedule.total_outages')} {len(schedule_cache.actual_schedules)}\n\n"

        # Group by date
        by_date = {}
        for schedule in schedule_cache.actual_schedules:
            date_key = schedule.date or "Unknown date"
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(schedule)

        for date_key in sorted(by_date.keys()):
            schedules = by_date[date_key]
            result += f"{i18n.t('schedule.date_label')} {date_key} ({schedules[0].day_of_week}):\n"

            # Count by type
            type_counts = {}
            for s in schedules:
                type_counts[s.outage_type] = type_counts.get(s.outage_type, 0) + 1

            result += f"  {i18n.t('schedule.definite_label')} {type_counts.get('definite', 0)}\n"
            result += f"  {i18n.t('schedule.first_30_label')} {type_counts.get('first_30min', 0)}\n"
            result += f"  {i18n.t('schedule.second_30_label')} {type_counts.get('second_30min', 0)}\n\n"
    else:
        result += f"{i18n.t('schedule.no_actual')}\n\n"

    # Possible schedule (if requested)
    if include_possible:
        result += "=" * 50 + "\n"
        result += f"📊 {i18n.t('schedule.possible_title')}\n"
        result += "=" * 50 + "\n\n"

        if schedule_cache.possible_schedules:
            result += f"{i18n.t('schedule.total_outages')} {len(schedule_cache.possible_schedules)}\n\n"

            # Group by day
            by_day = {}
            for schedule in schedule_cache.possible_schedules:
                day = schedule.day_of_week
                if day not in by_day:
                    by_day[day] = []
                by_day[day].append(schedule)

            days_order = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]
            for day in days_order:
                if day in by_day:
                    schedules = by_day[day]
                    result += f"  {day}: {len(schedules)} {i18n.t('schedule.hours_label')}\n"

            result += "\n"
        else:
            result += f"{i18n.t('schedule.no_possible')}\n\n"

    result += f"\n{i18n.t('schedule.hint_title')}\n"
    result += f"  • {i18n.t('schedule.hint_next_outage')}\n"
    result += f"  • {i18n.t('schedule.hint_outages_for_day')}\n"

    return result


async def handle_configure_monitoring(arguments: dict) -> list[TextContent]:
    """Handle configure_monitoring tool."""
    # Get current monitoring config
    monitoring = config.get_monitoring()
    was_enabled = monitoring.enabled

    # Update with provided arguments
    if "notification_before_minutes" in arguments:
        monitoring.notification_before_minutes = arguments["notification_before_minutes"]
    if "enabled" in arguments:
        monitoring.enabled = arguments["enabled"]
    if "check_interval_minutes" in arguments:
        monitoring.check_interval_minutes = arguments["check_interval_minutes"]

    # Save updated config
    config.update_monitoring(
        notification_before_minutes=monitoring.notification_before_minutes,
        enabled=monitoring.enabled,
        check_interval_minutes=monitoring.check_interval_minutes
    )

    # Set up or remove automatic monitoring based on enabled state
    setup_message = ""
    if monitoring.enabled and not was_enabled:
        # Enabling monitoring - set up automatic checks
        logger.info("Setting up automatic monitoring...")
        success, message = setup_monitoring(monitoring.check_interval_minutes)
        if success:
            setup_message = f"\n\n🤖 Automatic monitoring activated!\n{message}"
        else:
            setup_message = f"\n\n⚠️ Could not set up automatic monitoring:\n{message}\n\nYou can still check manually by asking: 'Check for upcoming outages'"
    elif not monitoring.enabled and was_enabled:
        # Disabling monitoring - remove automatic checks
        logger.info("Removing automatic monitoring...")
        success, message = remove_monitoring()
        if success:
            setup_message = f"\n\n{message}"
        else:
            setup_message = f"\n\n⚠️ Could not remove automatic monitoring:\n{message}"
    elif monitoring.enabled and was_enabled:
        # Updating monitoring settings - reconfigure
        logger.info("Updating automatic monitoring...")
        success, message = setup_monitoring(monitoring.check_interval_minutes)
        if success:
            setup_message = f"\n\n🔄 Monitoring updated!\n{message}"

    # Format response
    enabled_text = "enabled" if monitoring.enabled else "disabled"

    base_message = i18n.t(
        "messages.monitoring_configured",
        enabled=enabled_text,
        minutes=monitoring.notification_before_minutes,
        interval=monitoring.check_interval_minutes
    )

    return [TextContent(
        type="text",
        text=base_message + setup_message
    )]


async def handle_check_upcoming_outages(arguments: dict) -> list[TextContent]:
    """Handle check_upcoming_outages tool."""
    # Get monitoring config first - check if enabled before anything else
    monitoring = config.get_monitoring()

    if not monitoring.enabled:
        return [TextContent(
            type="text",
            text=i18n.t("messages.monitoring_disabled")
        )]

    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_not_configured")
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_schedule_data")
        )]

    # Find upcoming outages within notification window
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute

    # Filter only actual schedules
    actual_schedules = [s for s in cached.actual_schedules if s.schedule_type == ScheduleType.ACTUAL]

    # Find outages starting within notification window
    upcoming_outages = []
    for schedule in actual_schedules:
        # Calculate time until outage starts
        time_until_outage_minutes = (schedule.start_hour - current_hour) * 60 - current_minute

        # Check if outage is within notification window
        if 0 <= time_until_outage_minutes <= monitoring.notification_before_minutes:
            upcoming_outages.append((schedule, time_until_outage_minutes))

    # If there are upcoming outages, send alert
    if upcoming_outages:
        # Get the closest outage
        closest_outage, minutes_until = min(upcoming_outages, key=lambda x: x[1])

        # Format outage details
        time_str = f"{closest_outage.start_hour:02d}:00-{closest_outage.end_hour:02d}:00"
        date_str = f"{closest_outage.date} " if closest_outage.date else ""
        outage_type_desc = i18n.t(f"messages.outage_types.{closest_outage.outage_type}")

        details = f"📅 {date_str}{closest_outage.day_of_week}\n"
        details += f"⏰ {time_str}\n"
        details += f"📊 {outage_type_desc}"

        return [TextContent(
            type="text",
            text=i18n.t(
                "messages.upcoming_outage_alert",
                minutes=int(minutes_until),
                details=details
            )
        )]

    # No upcoming outages - find next scheduled outage for informational purposes
    today_date = now.strftime("%d.%m.%y")
    next_outage = None
    for schedule in actual_schedules:
        # Check if this is today's schedule
        if schedule.date == today_date:
            # For today, only consider outages that haven't started yet
            if schedule.start_hour > current_hour:
                next_outage = schedule
                break
        else:
            # For future dates (tomorrow), take the first one
            next_outage = schedule
            break

    if not next_outage and actual_schedules:
        # If no outage today and no future dates found, take first schedule as fallback
        next_outage = actual_schedules[0]

    if next_outage:
        time_str = f"{next_outage.start_hour:02d}:00-{next_outage.end_hour:02d}:00"
        date_str = f"{next_outage.date} " if next_outage.date else ""
        outage_type_desc = i18n.t(f"messages.outage_types.{next_outage.outage_type}")

        next_outage_info = f"  {date_str}{next_outage.day_of_week}, {time_str}\n"
        next_outage_info += f"  {outage_type_desc}"
    else:
        next_outage_info = i18n.t("messages.no_next_outage")

    return [TextContent(
        type="text",
        text=i18n.t(
            "messages.no_upcoming_outages",
            minutes=monitoring.notification_before_minutes,
            next_outage=next_outage_info
        )
    )]


async def handle_calculate_charging_time(arguments: dict) -> list[TextContent]:
    """
    Handle calculate_charging_time tool.

    Automatically retrieves battery info from MacBook and calculates
    when to start charging to reach target percentage before next outage.
    """
    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text=i18n.t("messages.address_not_configured")
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return [TextContent(
            type="text",
            text=i18n.t("messages.no_schedule_for_charging")
        )]

    # Get battery info automatically (MAGIC!)
    battery = get_battery_info()
    if not battery:
        return [TextContent(
            type="text",
            text=i18n.t("messages.battery_info_unavailable_bridge")
        )]

    current_charge = battery.current_charge_percent
    capacity_wh = battery.capacity_wh
    charging_power_w = battery.charging_power_w or estimate_charging_power()

    # Get target percentages (default: [80, 100])
    targets = arguments.get("target_charge_percent")
    if targets:
        target_percents = [targets] if isinstance(targets, int) else targets
    else:
        target_percents = get_default_target_percents()

    # Build response header
    result = f"{i18n.t('messages.charging_recommendation_title')}\n\n"
    result += f"🔋 {i18n.t('messages.battery_status')}\n"
    result += f"  • {i18n.t('messages.current_charge')}: {current_charge}%\n"
    result += f"  • {i18n.t('messages.battery_capacity')}: {capacity_wh:.1f} Wh\n"
    result += f"  • {i18n.t('messages.charging_status')}: "
    if battery.is_charging:
        result += f"{i18n.t('messages.charging_yes')} ({battery.charging_power_w:.1f}W)\n"
    else:
        result += f"{i18n.t('messages.charging_no')}"
        if battery.discharge_rate_w:
            result += f" ({i18n.t('messages.consuming')} {battery.discharge_rate_w:.1f}W)\n"
        else:
            result += "\n"
    result += "\n"

    # Get current time
    now = datetime.now()
    current_date = now.strftime("%d.%m.%y")
    current_hour = now.hour
    current_minute = now.minute

    # Get actual schedules only
    actual_schedules = [s for s in cached.actual_schedules if s.schedule_type == ScheduleType.ACTUAL]

    # Find next outage
    next_outage = None
    next_outage_time = None

    for schedule in actual_schedules:
        if schedule.date == current_date:
            # For today, only consider outages that haven't started yet
            if schedule.start_hour > current_hour or (schedule.start_hour == current_hour and current_minute < 60):
                next_outage = schedule
                # Calculate time until outage in hours
                next_outage_time = schedule.start_hour + (0 / 60) - (current_hour + current_minute / 60)
                break
        else:
            # Future dates - take first outage
            next_outage = schedule
            # Rough estimate: assume it's tomorrow
            next_outage_time = (24 - current_hour) + schedule.start_hour - (current_minute / 60)
            break

    if not next_outage:
        result += i18n.t("messages.no_upcoming_outages_for_charging")
        return [TextContent(type="text", text=result)]

    # Calculate recommendations for each target percentage
    recommendations = []

    for target_percent in target_percents:
        if target_percent <= current_charge:
            continue  # Already at or above this target

        # Calculate how much charge is needed
        charge_needed_percent = target_percent - current_charge
        charge_needed_wh = capacity_wh * (charge_needed_percent / 100)

        # Calculate charging time needed
        charging_time_hours = charge_needed_wh / charging_power_w

        # Calculate when to start charging to finish before outage
        time_before_outage_to_start = next_outage_time - charging_time_hours

        # Format charging time
        hours_int = int(charging_time_hours)
        minutes_int = int((charging_time_hours - hours_int) * 60)

        # Calculate actual start time
        start_hour = current_hour + int(time_before_outage_to_start)
        start_minute = current_minute + int((time_before_outage_to_start - int(time_before_outage_to_start)) * 60)

        if start_minute >= 60:
            start_hour += 1
            start_minute -= 60

        # Calculate completion time
        completion_hour = start_hour + hours_int
        completion_minute = start_minute + minutes_int
        if completion_minute >= 60:
            completion_hour += 1
            completion_minute -= 60

        recommendations.append({
            'target': target_percent,
            'charge_needed_wh': charge_needed_wh,
            'charging_time_hours': charging_time_hours,
            'hours': hours_int,
            'minutes': minutes_int,
            'time_before_outage_to_start': time_before_outage_to_start,
            'start_hour': start_hour % 24,
            'start_minute': start_minute,
            'completion_hour': completion_hour % 24,
            'completion_minute': completion_minute,
            'can_charge_now': time_before_outage_to_start <= 0
        })

    if not recommendations:
        result += i18n.t("messages.already_charged")
        return [TextContent(type="text", text=result)]

    # Show next outage info
    outage_time_str = f"{next_outage.start_hour:02d}:00"
    result += f"⚠️ {i18n.t('messages.next_outage_at')}: {next_outage.date} {next_outage.day_of_week}, {outage_time_str}\n"
    result += f"   ({i18n.t('messages.in_hours', hours=round(next_outage_time, 1))})\n\n"

    # Show recommendations
    result += f"📱 {i18n.t('messages.charging_recommendations')}:\n\n"

    for rec in recommendations:
        target_emoji = "🟢" if rec['target'] == 80 else "🔋"
        result += f"{target_emoji} {i18n.t('messages.target_label')}: {rec['target']}%\n"
        result += f"   • {i18n.t('messages.charging_time_needed')}: {rec['hours']}h {rec['minutes']}m\n"

        if rec['can_charge_now']:
            result += f"   • {i18n.t('messages.start_charging')}: {i18n.t('messages.now_immediately')} ⚡\n"
        else:
            start_time_str = f"{rec['start_hour']:02d}:{rec['start_minute']:02d}"
            result += f"   • {i18n.t('messages.start_charging')}: {start_time_str}\n"

        completion_str = f"{rec['completion_hour']:02d}:{rec['completion_minute']:02d}"
        result += f"   • {i18n.t('messages.finish_charging')}: {completion_str} ({i18n.t('messages.before_outage')})\n"
        result += "\n"

    # Add recommendation
    priority_rec = recommendations[0]  # First target (usually 80%)

    if priority_rec['can_charge_now']:
        result += f"✅ {i18n.t('messages.recommendation')}: {i18n.t('messages.plug_in_now')}\n"
    else:
        start_time_str = f"{priority_rec['start_hour']:02d}:{priority_rec['start_minute']:02d}"
        result += f"💡 {i18n.t('messages.recommendation')}: {i18n.t('messages.plug_in_at', time=start_time_str)}\n"

    return [TextContent(type="text", text=result)]


async def main():
    """Run the MCP server."""
    logger.info("Starting Electricity Shutdowns MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
