"""
Unit tests for DTEK parser module.

These tests focus on testing individual parsing methods with mock HTML data,
without requiring actual network requests to the DTEK website.
"""
import sys
sys.path.insert(0, 'src')

import pytest
from parser import DTEKParser
from config import OutageType, ScheduleType


class TestOutageTypeDetection:
    """Test _detect_outage_type_from_class method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DTEKParser()

    def test_detect_definite_outage(self):
        """Test detection of definite outage."""
        result = self.parser._detect_outage_type_from_class(['cell-scheduled'])
        assert result == OutageType.DEFINITE

    def test_detect_first_30_min_outage(self):
        """Test detection of first 30 minutes outage."""
        result = self.parser._detect_outage_type_from_class(['cell-first-half'])
        assert result == OutageType.FIRST_30_MIN

    def test_detect_second_30_min_outage(self):
        """Test detection of second 30 minutes outage."""
        result = self.parser._detect_outage_type_from_class(['cell-second-half'])
        assert result == OutageType.SECOND_30_MIN

    def test_detect_possible_outage(self):
        """Test detection of possible outage."""
        result = self.parser._detect_outage_type_from_class(['cell-scheduled-maybe'])
        assert result == OutageType.POSSIBLE

    def test_detect_no_outage(self):
        """Test detection when there's no outage."""
        result = self.parser._detect_outage_type_from_class(['cell-non-scheduled'])
        assert result is None

    def test_detect_with_multiple_classes(self):
        """Test detection with multiple CSS classes."""
        result = self.parser._detect_outage_type_from_class(['some-class', 'cell-scheduled', 'another-class'])
        assert result == OutageType.DEFINITE

    def test_detect_with_empty_list(self):
        """Test detection with empty class list."""
        result = self.parser._detect_outage_type_from_class([])
        assert result is None


class TestActualScheduleParsing:
    """Test _parse_actual_schedule method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DTEKParser()

    def test_parse_actual_schedule_with_valid_html(self):
        """Test parsing actual schedule with valid HTML."""
        html = """
        <html>
            <div class="dates">
                <div class="active">
                    <span rel="date">15.11.25</span>
                    сьогодні
                </div>
            </div>
            <div class="discon-fact-table active">
                <table>
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                            <th>00-01</th>
                            <th>01-02</th>
                            <th>02-03</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td></td>
                            <td></td>
                            <td class="cell-scheduled"></td>
                            <td class="cell-first-half"></td>
                            <td class="cell-non-scheduled"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </html>
        """

        schedules = self.parser._parse_actual_schedule(html)

        # Should parse 2 outages (00-01 definite, 01-02 first 30 min)
        assert len(schedules) == 2

        # Get expected day of week for today
        from datetime import datetime
        day_idx = datetime.now().weekday()
        days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
        expected_day = days[day_idx]

        # Check first outage
        assert schedules[0].schedule_type == ScheduleType.ACTUAL
        assert schedules[0].date == "15.11.25"
        assert schedules[0].day_of_week == expected_day
        assert schedules[0].start_hour == 0
        assert schedules[0].end_hour == 1
        assert schedules[0].outage_type == OutageType.DEFINITE

        # Check second outage
        assert schedules[1].start_hour == 1
        assert schedules[1].end_hour == 2
        assert schedules[1].outage_type == OutageType.FIRST_30_MIN

    def test_parse_actual_schedule_with_no_table(self):
        """Test parsing when table is missing."""
        html = """
        <html>
            <div class="discon-fact-table active">
                <!-- No table -->
            </div>
        </html>
        """

        schedules = self.parser._parse_actual_schedule(html)
        assert len(schedules) == 0

    def test_parse_actual_schedule_with_no_active_div(self):
        """Test parsing when active div is missing."""
        html = """
        <html>
            <div class="discon-fact-table">
                <!-- Not active -->
            </div>
        </html>
        """

        schedules = self.parser._parse_actual_schedule(html)
        assert len(schedules) == 0

    def test_parse_actual_schedule_with_tomorrow_date(self):
        """Test parsing with tomorrow's date."""
        html = """
        <html>
            <div class="dates">
                <div class="active">
                    <span rel="date">16.11.25</span>
                    завтра
                </div>
            </div>
            <div class="discon-fact-table active">
                <table>
                    <thead>
                        <tr>
                            <th></th>
                            <th></th>
                            <th>10-11</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td></td>
                            <td></td>
                            <td class="cell-scheduled"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </html>
        """

        schedules = self.parser._parse_actual_schedule(html)

        # Get expected day of week for tomorrow
        from datetime import datetime, timedelta
        day_idx = (datetime.now() + timedelta(days=1)).weekday()
        days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
        expected_day = days[day_idx]

        assert len(schedules) == 1
        assert schedules[0].date == "16.11.25"
        assert schedules[0].day_of_week == expected_day
        assert schedules[0].start_hour == 10
        assert schedules[0].end_hour == 11


class TestPossibleScheduleParsing:
    """Test _parse_possible_schedule method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = DTEKParser()

    def test_parse_possible_schedule_with_valid_html(self):
        """Test parsing possible schedule with valid HTML."""
        html = """
        <html>
            <div class="discon-schedule-table">
                <table>
                    <thead>
                        <tr>
                            <th></th>
                            <th>День тижня</th>
                            <th>00-01</th>
                            <th>01-02</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Понеділок</td>
                            <td class="cell-scheduled-maybe"></td>
                            <td class="cell-non-scheduled"></td>
                        </tr>
                        <tr>
                            <td>Вівторок</td>
                            <td class="cell-scheduled-maybe"></td>
                            <td class="cell-scheduled-maybe"></td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </html>
        """

        schedules = self.parser._parse_possible_schedule(html)

        # Should parse 3 possible outages (Monday 1, Tuesday 2)
        assert len(schedules) == 3

        # Check Monday outage
        assert schedules[0].schedule_type == ScheduleType.POSSIBLE_WEEK
        assert schedules[0].day_of_week == "Понеділок"
        assert schedules[0].start_hour == 0
        assert schedules[0].end_hour == 1
        assert schedules[0].outage_type == OutageType.POSSIBLE

        # Check Tuesday outages
        assert schedules[1].day_of_week == "Вівторок"
        assert schedules[1].start_hour == 0
        assert schedules[2].start_hour == 1

    def test_parse_possible_schedule_with_no_table(self):
        """Test parsing when table is missing."""
        html = """
        <html>
            <div class="discon-schedule-table">
                <!-- No table -->
            </div>
        </html>
        """

        schedules = self.parser._parse_possible_schedule(html)
        assert len(schedules) == 0

    def test_parse_possible_schedule_with_no_div(self):
        """Test parsing when div is missing."""
        html = """
        <html>
            <!-- No discon-schedule-table div -->
        </html>
        """

        schedules = self.parser._parse_possible_schedule(html)
        assert len(schedules) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
