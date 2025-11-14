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

    # Fetch fresh data
    logger.info(f"Fetching schedule for {address.to_string()}")
    try:
        schedule_cache = await fetch_dtek_schedule(
            city=address.city,
            street=address.street,
            house_number=address.house_number,
            include_possible=include_possible
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

    # Filter only actual schedules and sort by date and hour
    actual_schedules = [s for s in cached.actual_schedules if s.schedule_type == ScheduleType.ACTUAL]

    # Find next outage (current or future)
    next_outage = None
    for schedule in actual_schedules:
        if schedule.start_hour >= current_hour:
            next_outage = schedule
            break

    if not next_outage and actual_schedules:
        # If no outage today, take first outage from tomorrow
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
