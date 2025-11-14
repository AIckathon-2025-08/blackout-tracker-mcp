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
            description=(
                "Перевіряє графік відключень електроенергії для налаштованої адреси. "
                "Повертає точний графік на сьогодні/завтра (ACTUAL) та опціонально прогноз на тиждень (POSSIBLE_WEEK). "
                "Перед використанням переконайтеся, що адресу налаштовано через set_address."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "include_possible": {
                        "type": "boolean",
                        "description": "Чи включати прогноз можливих відключень на тиждень (додатково до точного графіка)",
                        "default": False
                    },
                    "force_refresh": {
                        "type": "boolean",
                        "description": "Примусово оновити дані з сайту (ігнорувати кеш)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="get_next_outage",
            description=(
                "Знаходить найближче наступне відключення електроенергії з точного графіка (ACTUAL). "
                "Показує коли і на який час заплановано відключення. "
                "Працює тільки з точним графіком на сьогодні/завтра."
            ),
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_outages_for_day",
            description=(
                "Отримує всі відключення для конкретного дня тижня. "
                "Можна отримати як точний графік (ACTUAL) для сьогодні/завтра, так і прогноз (POSSIBLE_WEEK)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "day_of_week": {
                        "type": "string",
                        "description": "День тижня українською: Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя"
                    },
                    "schedule_type": {
                        "type": "string",
                        "enum": ["actual", "possible_week"],
                        "description": "Тип графіка: 'actual' - точний графік (сьогодні/завтра), 'possible_week' - прогноз на тиждень",
                        "default": "actual"
                    }
                },
                "required": ["day_of_week"]
            }
        ),
        Tool(
            name="set_address",
            description=(
                "Налаштовує адресу користувача для перевірки графіка відключень. "
                "Адреса зберігається і використовується для всіх наступних запитів. "
                "Важливо: місто і вулиця повинні мати правильні префікси (м., Просп., Вул. і т.д.), "
                "як вони з'являються в автозаповненні на сайті ДТЕК."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Місто з префіксом, наприклад: 'м. Дніпро', 'м. Київ'"
                    },
                    "street": {
                        "type": "string",
                        "description": "Вулиця з префіксом, наприклад: 'Просп. Миру', 'Вул. Шевченка'"
                    },
                    "house_number": {
                        "type": "string",
                        "description": "Номер будинку, наприклад: '4', '50а'"
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
            text="Помилка: необхідно вказати місто, вулицю і номер будинку."
        )]

    # Save address to config
    config.set_address(city=city, street=street, house_number=house_number)

    return [TextContent(
        type="text",
        text=f"✓ Адресу збережено: {city}, {street}, буд. {house_number}\n\n"
             f"Тепер можна використовувати check_outage_schedule для перевірки графіка відключень."
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
            text="Помилка: адреса не налаштована. Спочатку використайте set_address."
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
            text=f"Помилка отримання графіка: {str(e)}\n\n"
                 f"Переконайтеся, що адреса вказана правильно і існує на сайті ДТЕК."
        )]


async def handle_get_next_outage(arguments: dict) -> list[TextContent]:
    """Handle get_next_outage tool."""
    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text="Помилка: адреса не налаштована. Спочатку використайте set_address."
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached or not cached.actual_schedules:
        return [TextContent(
            type="text",
            text="Немає даних про графік відключень. Спочатку виконайте check_outage_schedule."
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
            text="Наступних відключень не знайдено в точному графіку."
        )]

    # Format response
    time_str = f"{next_outage.start_hour:02d}:00-{next_outage.end_hour:02d}:00"
    date_str = f"{next_outage.date} " if next_outage.date else ""

    outage_type_desc = {
        "definite": "Точне відключення ✗",
        "first_30min": "Світла не буде перші 30 хв ⚡",
        "second_30min": "Світла можливо не буде другі 30 хв ⚡",
        "possible": "Можливе відключення"
    }.get(next_outage.outage_type, next_outage.outage_type)

    return [TextContent(
        type="text",
        text=f"📍 Адреса: {address.to_string()}\n\n"
             f"⏰ Наступне відключення:\n"
             f"  {date_str}{next_outage.day_of_week}, {time_str}\n"
             f"  Тип: {outage_type_desc}\n\n"
             f"Дані оновлено: {cached.last_updated.strftime('%d.%m.%Y %H:%M')}"
    )]


async def handle_get_outages_for_day(arguments: dict) -> list[TextContent]:
    """Handle get_outages_for_day tool."""
    day_of_week = arguments.get("day_of_week", "").strip()
    schedule_type = arguments.get("schedule_type", "actual")

    if not day_of_week:
        return [TextContent(
            type="text",
            text="Помилка: необхідно вказати день тижня (Понеділок, Вівторок, і т.д.)"
        )]

    # Check if address is configured
    address = config.get_address()
    if not address:
        return [TextContent(
            type="text",
            text="Помилка: адреса не налаштована. Спочатку використайте set_address."
        )]

    # Load schedule from cache
    cached = config.load_schedule_cache()
    if not cached:
        return [TextContent(
            type="text",
            text="Немає даних про графік відключень. Спочатку виконайте check_outage_schedule."
        )]

    # Filter schedules by day and type
    if schedule_type == ScheduleType.ACTUAL:
        schedules = [s for s in cached.actual_schedules
                    if s.day_of_week == day_of_week and s.schedule_type == ScheduleType.ACTUAL]
        schedule_type_label = "Точний графік"
    else:
        schedules = [s for s in cached.possible_schedules
                    if s.day_of_week == day_of_week and s.schedule_type == ScheduleType.POSSIBLE_WEEK]
        schedule_type_label = "Прогноз можливих відключень"

    if not schedules:
        return [TextContent(
            type="text",
            text=f"Відключень не знайдено для дня: {day_of_week} ({schedule_type_label})"
        )]

    # Format response
    result = f"📍 Адреса: {address.to_string()}\n"
    result += f"📅 День: {day_of_week}\n"
    result += f"📊 Тип: {schedule_type_label}\n\n"
    result += f"Відключення ({len(schedules)}):\n"

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

    result += f"\nДані оновлено: {cached.last_updated.strftime('%d.%m.%Y %H:%M')}"

    return [TextContent(type="text", text=result)]


def format_schedule_response(
    schedule_cache,
    address,
    include_possible: bool,
    from_cache: bool
) -> str:
    """Format schedule data into readable response."""
    result = f"📍 Адреса: {address.to_string()}\n"
    result += f"🔄 Джерело: {'Кеш' if from_cache else 'Свіже з сайту'}\n"
    result += f"⏰ Оновлено: {schedule_cache.last_updated.strftime('%d.%m.%Y %H:%M')}\n\n"

    # Actual schedule
    result += "=" * 50 + "\n"
    result += "📊 ТОЧНИЙ ГРАФІК (сьогодні/завтра)\n"
    result += "=" * 50 + "\n\n"

    if schedule_cache.actual_schedules:
        result += f"Всього відключень: {len(schedule_cache.actual_schedules)}\n\n"

        # Group by date
        by_date = {}
        for schedule in schedule_cache.actual_schedules:
            date_key = schedule.date or "Невідома дата"
            if date_key not in by_date:
                by_date[date_key] = []
            by_date[date_key].append(schedule)

        for date_key in sorted(by_date.keys()):
            schedules = by_date[date_key]
            result += f"📅 {date_key} ({schedules[0].day_of_week}):\n"

            # Count by type
            type_counts = {}
            for s in schedules:
                type_counts[s.outage_type] = type_counts.get(s.outage_type, 0) + 1

            result += f"  ✗ Точні: {type_counts.get('definite', 0)}\n"
            result += f"  ⚡ Перші 30хв: {type_counts.get('first_30min', 0)}\n"
            result += f"  ⚡* Другі 30хв: {type_counts.get('second_30min', 0)}\n\n"
    else:
        result += "Точних відключень не знайдено.\n\n"

    # Possible schedule (if requested)
    if include_possible:
        result += "=" * 50 + "\n"
        result += "📊 ПРОГНОЗ НА ТИЖДЕНЬ (можливі відключення)\n"
        result += "=" * 50 + "\n\n"

        if schedule_cache.possible_schedules:
            result += f"Всього можливих відключень: {len(schedule_cache.possible_schedules)}\n\n"

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
                    result += f"  {day}: {len(schedules)} годин\n"

            result += "\n"
        else:
            result += "Прогноз не знайдено.\n\n"

    result += "\n💡 Підказка:\n"
    result += "  • Використайте get_next_outage для швидкого пошуку наступного відключення\n"
    result += "  • Використайте get_outages_for_day для детального графіка на конкретний день\n"

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
