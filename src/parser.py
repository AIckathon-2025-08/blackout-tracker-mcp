"""
DTEK website parser for electricity shutdown schedules.
"""
import asyncio
import re
from datetime import datetime
from typing import Optional
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

from config import OutageSchedule, ScheduleType, OutageType, ScheduleCache


class DTEKParserError(Exception):
    """Base exception for DTEK parser errors."""
    pass


class AddressNotFoundError(DTEKParserError):
    """Address not found in DTEK database."""
    pass


class PageLoadError(DTEKParserError):
    """Failed to load DTEK page."""
    pass


class DTEKParser:
    """Parser for DTEK Dnipro electricity shutdown schedules."""

    DTEK_URL = "https://www.dtek-dnem.com.ua/ua/shutdowns"

    def __init__(self, headless: bool = True):
        """
        Initialize DTEK parser.

        Args:
            headless: Run browser in headless mode (default: True)
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Start browser and initialize page."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=self.headless)
        self.page = await self.browser.new_page()

        # Set Ukrainian locale
        await self.page.set_extra_http_headers({"Accept-Language": "uk-UA,uk;q=0.9"})

    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()

    async def fetch_schedule(
        self,
        city: str,
        street: str,
        house_number: str,
        include_possible: bool = True
    ) -> ScheduleCache:
        """
        Fetch electricity shutdown schedule for given address.

        Args:
            city: City name (e.g., "м. Дніпро")
            street: Street name with prefix (e.g., "Просп. Миру")
            house_number: House number (e.g., "4", "50а")
            include_possible: Include possible weekly schedule (default: True)

        Returns:
            ScheduleCache with actual and possible schedules

        Raises:
            AddressNotFoundError: If address not found
            PageLoadError: If page fails to load
        """
        if not self.page:
            await self.start()

        # Navigate to DTEK page
        try:
            await self.page.goto(self.DTEK_URL, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeout:
            raise PageLoadError(f"Failed to load {self.DTEK_URL}")

        # Close modal warning if it appears
        await self._close_modal_if_present()

        # Fill the form
        await self._fill_address_form(city, street, house_number)

        # Wait for schedule tables to load
        await self._wait_for_schedule_tables()

        # Get page HTML
        html = await self.page.content()

        # Parse schedules
        actual_schedules = self._parse_actual_schedule(html)
        possible_schedules = []
        if include_possible:
            possible_schedules = self._parse_possible_schedule(html)

        return ScheduleCache(
            actual_schedules=actual_schedules,
            possible_schedules=possible_schedules,
            last_updated=datetime.now()
        )

    async def _close_modal_if_present(self):
        """Close modal warning window if it appears."""
        try:
            # Wait a bit for modal to appear
            await asyncio.sleep(1)

            # Try different selectors for close button (X icon)
            close_selectors = [
                'button[aria-label*="lose"]',  # aria-label="Close"
                'button[aria-label*="акрити"]',  # Ukrainian "Закрити"
                '.MuiDialog-root button[aria-label]',  # Material-UI dialog close button
                '.modal-close',
                '.close-button',
                'button.close',
                '[data-dismiss="modal"]',
                '.modal button[type="button"]',
                # SVG close icons
                'button svg[data-testid*="CloseIcon"]',
                'button svg[class*="close"]',
            ]

            for selector in close_selectors:
                try:
                    close_button = await self.page.query_selector(selector)
                    if close_button and await close_button.is_visible():
                        print(f"Found modal close button with selector: {selector}")
                        await close_button.click()
                        await asyncio.sleep(0.5)
                        print("Modal closed successfully")
                        return
                except Exception:
                    continue

            # If no close button found, try ESC key
            try:
                await self.page.keyboard.press('Escape')
                await asyncio.sleep(0.5)
            except:
                pass

        except Exception as e:
            # If modal handling fails, it's not critical - continue
            print(f"Note: Could not close modal (might not be present): {e}")

    async def _fill_address_form(self, city: str, street: str, house_number: str):
        """
        Fill address form on DTEK website.

        Args:
            city: City name (e.g., "м. Дніпро" or just "Дніпро")
            street: Street name (e.g., "Просп. Миру" or just "Миру")
            house_number: House number (e.g., "4")
        """
        # Wait for form to be visible
        await asyncio.sleep(1)

        # Fill city field using ID selector
        city_input = await self.page.query_selector('#city')
        if not city_input:
            city_input = await self.page.query_selector('input[name="city"]')

        if city_input:
            await city_input.click()
            await city_input.fill(city)
            # Give time for autocomplete to trigger
            await asyncio.sleep(1.5)

            # Wait for custom autocomplete dropdown and select first option
            try:
                # Custom autocomplete uses id="cityautocomplete-list"
                await self.page.wait_for_selector('#cityautocomplete-list > div', timeout=10000)
                # Click first option (which contains <strong>м. дніпро</strong>)
                await self.page.click('#cityautocomplete-list > div:first-child')
                print(f"Selected city from dropdown")

                # IMPORTANT: Wait for dropdown to disappear before moving to next field
                await self.page.wait_for_selector('#cityautocomplete-list', state='hidden', timeout=5000)
                print("City dropdown closed, street field should be enabled now")
            except Exception as e:
                print(f"Warning: Could not select city from dropdown: {e}")
                # If no dropdown appears, press Enter
                await city_input.press('Enter')
        else:
            raise PageLoadError("Could not find city input field")

        # Wait for street field to become enabled after city selection
        await asyncio.sleep(1)

        # Fill street field using ID selector
        street_input = await self.page.query_selector('#street')
        if not street_input:
            street_input = await self.page.query_selector('input[name="street"]')

        if street_input:
            # Wait until input is enabled
            try:
                await street_input.wait_for_element_state("enabled", timeout=5000)
                print("Street field is now enabled")
            except:
                print("Warning: Street input might not be fully enabled, trying anyway...")

            await street_input.click()
            await street_input.fill(street)
            await asyncio.sleep(1.5)

            # Wait for custom autocomplete dropdown and select matching option
            try:
                # Custom autocomplete uses id="streetautocomplete-list"
                await self.page.wait_for_selector('#streetautocomplete-list > div', timeout=10000)
                # Click first matching option
                await self.page.click('#streetautocomplete-list > div:first-child')
                print(f"Selected street from dropdown")

                # IMPORTANT: Wait for dropdown to disappear before moving to next field
                await self.page.wait_for_selector('#streetautocomplete-list', state='hidden', timeout=5000)
                print("Street dropdown closed, house field should be enabled now")
            except Exception as e:
                print(f"Warning: Could not select street from dropdown: {e}")
                # Try pressing Enter
                await street_input.press('Enter')
        else:
            raise PageLoadError("Could not find street input field")

        # Wait for house field to become enabled after street selection
        await asyncio.sleep(1)

        # Fill house number field using ID selector
        house_input = await self.page.query_selector('#house_num')
        if not house_input:
            house_input = await self.page.query_selector('input[name="house_num"]')

        if house_input:
            # Wait until input is enabled
            try:
                await house_input.wait_for_element_state("enabled", timeout=5000)
                print("House field is now enabled")
            except:
                print("Warning: House input might not be fully enabled, trying anyway...")

            await house_input.click()
            await house_input.fill(house_number)
            await asyncio.sleep(1)

            # Wait for custom autocomplete dropdown and select first option
            try:
                # Custom autocomplete uses id="house_numautocomplete-list"
                await self.page.wait_for_selector('#house_numautocomplete-list > div', timeout=10000)
                await self.page.click('#house_numautocomplete-list > div:first-child')
                print(f"Selected house from dropdown")

                # IMPORTANT: Wait for dropdown to disappear - this triggers schedule load
                await self.page.wait_for_selector('#house_numautocomplete-list', state='hidden', timeout=5000)
                print("House dropdown closed, schedule should start loading")
            except Exception as e:
                print(f"Warning: Could not select house from dropdown: {e}")
                await house_input.press('Enter')
        else:
            raise PageLoadError("Could not find house number input field")

        # Wait for schedule to load after form is fully submitted
        print("Waiting for schedule tables to load...")
        await asyncio.sleep(4)

    async def _wait_for_schedule_tables(self):
        """Wait for schedule tables to appear on the page."""
        # TODO: Wait for specific elements that indicate tables are loaded
        # For now, just wait a bit
        await asyncio.sleep(2)

    def _parse_actual_schedule(self, html: str) -> list[OutageSchedule]:
        """
        Parse "Графік відключень:" table (actual schedule for today/tomorrow).

        Args:
            html: Page HTML content

        Returns:
            List of OutageSchedule objects for actual schedule
        """
        soup = BeautifulSoup(html, 'lxml')
        schedules = []

        try:
            # Find div with class="discon-fact-table active"
            actual_table_div = soup.find('div', class_=lambda x: x and 'discon-fact-table' in x and 'active' in x)

            if not actual_table_div:
                print("Warning: Could not find active actual schedule table (div.discon-fact-table.active)")
                return schedules

            # Extract date from rel attribute or from .dates div
            date_str = None
            day_of_week = None

            # Try to find date from .dates div
            dates_div = soup.find('div', class_='dates')
            if dates_div:
                active_date = dates_div.find('div', class_='active')
                if active_date:
                    date_span = active_date.find('span', attrs={'rel': 'date'})
                    if date_span:
                        date_str = date_span.get_text().strip()
                        # Determine day of week from text
                        date_text = active_date.get_text()
                        if 'сьогодні' in date_text.lower():
                            from datetime import datetime
                            day_idx = datetime.now().weekday()
                            days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
                            day_of_week = days[day_idx]
                        elif 'завтра' in date_text.lower():
                            from datetime import datetime, timedelta
                            day_idx = (datetime.now() + timedelta(days=1)).weekday()
                            days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
                            day_of_week = days[day_idx]

            # Find table inside
            table = actual_table_div.find('table')
            if not table:
                print("Warning: Could not find table inside actual schedule div")
                return schedules

            # Get time intervals from header
            header_row = table.find('thead').find('tr')
            time_cells = header_row.find_all('th')[2:]  # Skip first 2 cells (colspan="2")
            time_intervals = []
            for cell in time_cells:
                time_text = cell.get_text().strip()
                time_match = re.match(r'(\d{2})-(\d{2})', time_text)
                if time_match:
                    start_hour = int(time_match.group(1))
                    end_hour = int(time_match.group(2))
                    time_intervals.append((start_hour, end_hour))

            # Parse data row
            tbody = table.find('tbody')
            if tbody:
                data_row = tbody.find('tr')
                if data_row:
                    cells = data_row.find_all('td')[2:]  # Skip first 2 cells (colspan="2")

                    for i, cell in enumerate(cells):
                        if i >= len(time_intervals):
                            break

                        start_hour, end_hour = time_intervals[i]

                        # Detect outage type from cell CSS class
                        outage_type = self._detect_outage_type_from_class(cell.get('class', []))

                        if outage_type:
                            schedules.append(OutageSchedule(
                                schedule_type=ScheduleType.ACTUAL,
                                day_of_week=day_of_week or "",
                                date=date_str or "",
                                start_hour=start_hour,
                                end_hour=end_hour,
                                outage_type=outage_type
                            ))

            print(f"Parsed {len(schedules)} actual outages")

        except Exception as e:
            print(f"Error parsing actual schedule: {e}")
            import traceback
            traceback.print_exc()

        return schedules

    def _parse_possible_schedule(self, html: str) -> list[OutageSchedule]:
        """
        Parse "Графік можливих відключень на тиждень:" table.

        Args:
            html: Page HTML content

        Returns:
            List of OutageSchedule objects for possible weekly schedule
        """
        soup = BeautifulSoup(html, 'lxml')
        schedules = []

        try:
            # Find div with class="discon-schedule-table"
            schedule_div = soup.find('div', class_='discon-schedule-table')

            if not schedule_div:
                print("Warning: Could not find possible schedule div (div.discon-schedule-table)")
                return schedules

            # Find table inside
            table = schedule_div.find('table')
            if not table:
                print("Warning: Could not find table in possible schedule div")
                return schedules

            # Get time intervals from header
            header_row = table.find('thead').find('tr')
            time_cells = header_row.find_all('th')[2:]  # Skip first 2 cells (colspan="2")
            time_intervals = []
            for cell in time_cells:
                time_text = cell.get_text().strip()
                time_match = re.match(r'(\d{2})-(\d{2})', time_text)
                if time_match:
                    start_hour = int(time_match.group(1))
                    end_hour = int(time_match.group(2))
                    time_intervals.append((start_hour, end_hour))

            # Parse data rows (one row per day of week)
            days_of_week = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']

            tbody = table.find('tbody')
            if tbody:
                for data_row in tbody.find_all('tr'):
                    cells = data_row.find_all('td')
                    if not cells or len(cells) < 3:
                        continue

                    # First cell (colspan="2") contains day of week
                    day_cell = cells[0]
                    day_text = day_cell.get_text().strip()

                    # Extract day name
                    day_of_week = None
                    for day in days_of_week:
                        if day in day_text:
                            day_of_week = day
                            break

                    if not day_of_week:
                        continue

                    # Process hour cells (skip first cell with day name)
                    hour_cells = cells[1:]

                    for i, cell in enumerate(hour_cells):
                        if i >= len(time_intervals):
                            break

                        start_hour, end_hour = time_intervals[i]

                        # Detect outage type from cell CSS class
                        outage_type = self._detect_outage_type_from_class(cell.get('class', []))

                        if outage_type:
                            schedules.append(OutageSchedule(
                                schedule_type=ScheduleType.POSSIBLE_WEEK,
                                day_of_week=day_of_week,
                                date=None,  # No specific date for weekly forecast
                                start_hour=start_hour,
                                end_hour=end_hour,
                                outage_type=outage_type
                            ))

            print(f"Parsed {len(schedules)} possible outages")

        except Exception as e:
            print(f"Error parsing possible schedule: {e}")
            import traceback
            traceback.print_exc()

        return schedules

    def _detect_outage_type_from_class(self, cell_classes: list) -> Optional[str]:
        """
        Detect outage type from table cell CSS classes.

        Args:
            cell_classes: List of CSS classes from <td> element

        Returns:
            OutageType constant or None if no outage
        """
        if not cell_classes:
            return None

        # Convert to string for easier checking
        classes_str = ' '.join(cell_classes) if isinstance(cell_classes, list) else str(cell_classes)

        # Check for different outage types
        if 'cell-scheduled' in classes_str and 'maybe' not in classes_str:
            return OutageType.DEFINITE  # Світла немає

        if 'cell-first-half' in classes_str:
            return OutageType.FIRST_30_MIN  # Перші 30 хв

        if 'cell-second-half' in classes_str:
            return OutageType.SECOND_30_MIN  # Другі 30 хв

        if 'cell-scheduled-maybe' in classes_str:
            return OutageType.POSSIBLE  # Можливо відключення

        if 'cell-non-scheduled' in classes_str:
            return None  # Світло є - не додаємо до schedules

        return None

    def _detect_outage_type(self, cell_html: str) -> Optional[str]:
        """
        Detect outage type from table cell HTML.

        Args:
            cell_html: HTML content of table cell

        Returns:
            OutageType constant or None if no outage
        """
        cell_html_lower = cell_html.lower()

        # Check for definite outage (✗ black icon)
        # Look for the X/cross icon or specific text
        if '✗' in cell_html or '✕' in cell_html or '×' in cell_html:
            # Check if it's not the lightning bolt with X
            if '⚡' not in cell_html and 'lightning' not in cell_html_lower:
                return OutageType.DEFINITE

        # Check for lightning bolt icon (⚡)
        if '⚡' in cell_html or 'lightning' in cell_html_lower or 'zap' in cell_html_lower:
            # Check for "star" or marker indicating second 30 min
            # This might be a CSS class, data attribute, or additional icon
            if ('star' in cell_html_lower or
                '☆' in cell_html or
                '★' in cell_html or
                'second' in cell_html_lower or
                'друг' in cell_html_lower):
                return OutageType.SECOND_30_MIN
            else:
                return OutageType.FIRST_30_MIN

        # Check for gray background or "possible" indicator
        # This is usually from the weekly forecast table
        if ('gray' in cell_html_lower or
            'grey' in cell_html_lower or
            'можлив' in cell_html_lower or
            'possible' in cell_html_lower):
            return OutageType.POSSIBLE

        # Check for specific CSS classes that might indicate outage type
        # Common patterns: "outage-definite", "outage-possible", etc.
        if 'definite' in cell_html_lower or 'точн' in cell_html_lower:
            return OutageType.DEFINITE

        if 'possible' in cell_html_lower or 'можлив' in cell_html_lower:
            return OutageType.POSSIBLE

        # Check if cell has any content indicating an outage
        # If cell is mostly empty, no outage
        text_content = BeautifulSoup(cell_html, 'lxml').get_text().strip()
        if len(text_content) < 2 and '✗' not in cell_html and '⚡' not in cell_html:
            return None

        # If we found some icon/marker but couldn't classify it, default to POSSIBLE
        if any(marker in cell_html for marker in ['<svg', '<path', '<icon', 'fa-']):
            return OutageType.POSSIBLE

        return None


# Convenience function
async def fetch_dtek_schedule(
    city: str,
    street: str,
    house_number: str,
    include_possible: bool = True
) -> ScheduleCache:
    """
    Fetch DTEK schedule (convenience function).

    Args:
        city: City name
        street: Street name with prefix
        house_number: House number
        include_possible: Include possible weekly schedule

    Returns:
        ScheduleCache with schedules
    """
    async with DTEKParser() as parser:
        return await parser.fetch_schedule(city, street, house_number, include_possible)


# For testing
if __name__ == "__main__":
    async def test():
        """Test parser with sample address."""
        try:
            cache = await fetch_dtek_schedule(
                city="м. Дніпро",
                street="Просп. Миру",
                house_number="4"
            )
            print(f"Fetched {len(cache.actual_schedules)} actual schedules")
            print(f"Fetched {len(cache.possible_schedules)} possible schedules")

            for schedule in cache.actual_schedules[:5]:
                print(schedule)
        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
