"""
End-to-end tests for MCP server workflows.

These tests verify complete user workflows by calling multiple tools
in sequence and verifying state changes.
"""
import sys
sys.path.insert(0, 'src')

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta

from server import (
    handle_set_address,
    handle_check_schedule,
    handle_get_next_outage,
    handle_get_outages_for_day,
    handle_configure_monitoring
)
from config import Address, ScheduleCache, OutageSchedule, ScheduleType, OutageType


@pytest.fixture
def mock_dtek_schedule():
    """Fixture providing mock DTEK schedule data."""
    now = datetime.now()
    today_date = now.strftime("%d.%m.%y")
    tomorrow = now + timedelta(days=1)
    tomorrow_date = tomorrow.strftime("%d.%m.%y")

    days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
    today_day = days[now.weekday()]
    tomorrow_day = days[tomorrow.weekday()]

    return ScheduleCache(
        actual_schedules=[
            # Today's outages
            OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week=today_day,
                date=today_date,
                start_hour=10,
                end_hour=11,
                outage_type=OutageType.DEFINITE
            ),
            OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week=today_day,
                date=today_date,
                start_hour=14,
                end_hour=15,
                outage_type=OutageType.FIRST_30_MIN
            ),
            # Tomorrow's outages
            OutageSchedule(
                schedule_type=ScheduleType.ACTUAL,
                day_of_week=tomorrow_day,
                date=tomorrow_date,
                start_hour=9,
                end_hour=10,
                outage_type=OutageType.DEFINITE
            ),
        ],
        possible_schedules=[
            OutageSchedule(
                schedule_type=ScheduleType.POSSIBLE_WEEK,
                day_of_week="Понеділок",
                date=None,
                start_hour=8,
                end_hour=9,
                outage_type=OutageType.POSSIBLE
            ),
        ],
        last_updated=datetime.now()
    )


class TestHappyPathWorkflow:
    """Test the happy path: set address → check schedule → get next outage."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, mock_dtek_schedule):
        """Test complete workflow from address setup to getting next outage."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            # Step 1: Set address
            result = await handle_set_address({
                "city": "Дніпро",
                "street": "Князя Володимира Великого",
                "house_number": "15"
            })

            # Verify address was saved
            mock_config.set_address.assert_called_once_with(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            assert len(result) == 1
            assert "Дніпро" in result[0].text

            # Step 2: Setup mocks for schedule check
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None  # No cache initially
            mock_fetch.return_value = mock_dtek_schedule
            mock_format.return_value = "Schedule with outages"

            # Step 2: Check schedule
            result = await handle_check_schedule({})

            # Verify schedule was fetched and saved
            mock_fetch.assert_called_once()
            mock_config.save_schedule_cache.assert_called_once()
            assert len(result) == 1

            # Step 3: Setup mocks for next outage
            mock_config.load_schedule_cache.return_value = mock_dtek_schedule

            # Step 3: Get next outage
            result = await handle_get_next_outage({})

            # Should return next outage information
            assert len(result) == 1
            assert result[0].text  # Should have content


class TestCacheWorkflow:
    """Test cache behavior across multiple requests."""

    @pytest.mark.asyncio
    async def test_cache_is_used_on_second_request(self, mock_dtek_schedule):
        """Test that second schedule check uses cache without fetching."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_format.return_value = "Schedule"

            # First request - no cache
            mock_config.load_schedule_cache.return_value = None
            mock_fetch.return_value = mock_dtek_schedule

            result1 = await handle_check_schedule({})

            # Should fetch
            assert mock_fetch.call_count == 1
            mock_config.save_schedule_cache.assert_called_once()

            # Second request - with fresh cache
            mock_config.load_schedule_cache.return_value = mock_dtek_schedule

            result2 = await handle_check_schedule({})

            # Should NOT fetch again (still 1 call)
            assert mock_fetch.call_count == 1
            # format_schedule_response should be called with from_cache=True
            assert mock_format.call_count == 2

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, mock_dtek_schedule):
        """Test that force_refresh=True fetches even with fresh cache."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = mock_dtek_schedule
            mock_fetch.return_value = mock_dtek_schedule
            mock_format.return_value = "Schedule"

            # Request with force_refresh
            result = await handle_check_schedule({"force_refresh": True})

            # Should fetch despite cache
            mock_fetch.assert_called_once()


class TestErrorRecoveryWorkflow:
    """Test error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_get_schedule_without_address_then_set_address(self):
        """Test attempting to get schedule without address, then setting it."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            # Step 1: Try to check schedule without address
            mock_config.get_address.return_value = None

            result = await handle_check_schedule({})

            # Should get error about missing address
            assert len(result) == 1
            # Should NOT fetch
            mock_fetch.assert_not_called()

            # Step 2: Set address
            result = await handle_set_address({
                "city": "Дніпро",
                "street": "Князя Володимира Великого",
                "house_number": "15"
            })

            mock_config.set_address.assert_called_once()

            # Step 3: Try schedule check again with address
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None
            mock_fetch.return_value = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_format.return_value = "Schedule"

            result = await handle_check_schedule({})

            # Should now fetch successfully
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_next_outage_without_schedule_data(self):
        """Test getting next outage when no schedule data is cached."""
        with patch('server.config') as mock_config:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None

            result = await handle_get_next_outage({})

            # Should get error about no schedule data
            assert len(result) == 1
            # Message should indicate need to fetch schedule


class TestDayFilteringWorkflow:
    """Test filtering outages by day of week."""

    @pytest.mark.asyncio
    async def test_get_outages_for_specific_day(self, mock_dtek_schedule):
        """Test getting outages for a specific day after checking schedule."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Step 1: Check schedule
            mock_config.load_schedule_cache.return_value = None
            mock_fetch.return_value = mock_dtek_schedule
            mock_format.return_value = "Schedule"

            await handle_check_schedule({})

            # Step 2: Get outages for Monday
            mock_config.load_schedule_cache.return_value = mock_dtek_schedule

            result = await handle_get_outages_for_day({
                "day_of_week": "Понеділок",
                "schedule_type": "possible_week"
            })

            # Should return Monday's possible outages
            assert len(result) == 1
            assert "Понеділок" in result[0].text


class TestMonitoringWorkflow:
    """Test monitoring configuration workflow."""

    @pytest.mark.asyncio
    async def test_configure_monitoring_and_check_upcoming(self):
        """Test configuring monitoring and checking upcoming outages."""
        with patch('server.config') as mock_config:

            # Step 1: Configure monitoring
            from config import MonitoringConfig
            mock_monitoring = MonitoringConfig(
                notification_before_minutes=60,
                enabled=False,
                check_interval_minutes=60
            )
            mock_config.get_monitoring.return_value = mock_monitoring

            result = await handle_configure_monitoring({
                "notification_before_minutes": 30,
                "enabled": True,
                "check_interval_minutes": 15
            })

            # Verify config was updated
            mock_config.update_monitoring.assert_called_once()
            assert mock_monitoring.notification_before_minutes == 30
            assert mock_monitoring.enabled == True
            assert mock_monitoring.check_interval_minutes == 15


class TestIncludePossibleParameter:
    """Test include_possible parameter in schedule checks."""

    @pytest.mark.asyncio
    async def test_schedule_with_and_without_possible(self, mock_dtek_schedule):
        """Test checking schedule with and without possible outages."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None
            mock_fetch.return_value = mock_dtek_schedule

            # Mock format_schedule_response to return different values based on include_possible
            def format_response(cache, address, include_possible, from_cache):
                if include_possible:
                    return "Schedule with possible outages"
                return "Schedule without possible outages"

            mock_format.side_effect = format_response

            # Check schedule without possible
            result1 = await handle_check_schedule({"include_possible": False})

            # Check format was called with include_possible=False
            call_args = mock_format.call_args
            assert call_args[0][2] == False  # include_possible parameter

            # Reset mocks
            mock_config.load_schedule_cache.return_value = mock_dtek_schedule
            mock_format.reset_mock()
            mock_format.side_effect = format_response

            # Check schedule with possible
            result2 = await handle_check_schedule({"include_possible": True})

            # Check format was called with include_possible=True
            call_args = mock_format.call_args
            assert call_args[0][2] == True  # include_possible parameter


class TestStaleCache:
    """Test stale cache detection and refresh."""

    @pytest.mark.asyncio
    async def test_stale_cache_triggers_refresh(self, mock_dtek_schedule):
        """Test that stale cache (>1 hour) triggers automatic refresh."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Setup stale cache (2 hours old)
            stale_cache = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now() - timedelta(hours=2)
            )
            mock_config.load_schedule_cache.return_value = stale_cache
            mock_fetch.return_value = mock_dtek_schedule
            mock_format.return_value = "Fresh schedule"

            result = await handle_check_schedule({})

            # Should fetch fresh data
            mock_fetch.assert_called_once()
            # Should save new cache
            mock_config.save_schedule_cache.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
