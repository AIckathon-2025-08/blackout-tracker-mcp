"""
Unit tests for MCP tool handlers.

These tests mock external dependencies (config, parser) to test
tool handler logic in isolation.
"""
import sys
sys.path.insert(0, 'src')

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from mcp.types import TextContent

# Import handlers from server
from server import (
    handle_set_address,
    handle_check_schedule,
    handle_get_next_outage,
    handle_get_outages_for_day,
    handle_configure_monitoring,
    handle_check_upcoming_outages
)
from config import Address, ScheduleCache, OutageSchedule, ScheduleType, OutageType


class TestSetAddress:
    """Test set_address tool handler."""

    @pytest.mark.asyncio
    async def test_valid_address(self):
        """Test setting a valid address."""
        with patch('server.config') as mock_config:
            result = await handle_set_address({
                "city": "Дніпро",
                "street": "Князя Володимира Великого",
                "house_number": "15"
            })

            # Should save address to config
            mock_config.set_address.assert_called_once_with(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )

            # Should return success message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Дніпро" in result[0].text
            assert "15" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_city(self):
        """Test with missing city parameter."""
        with patch('server.config') as mock_config:
            result = await handle_set_address({
                "street": "Князя Володимира Великого",
                "house_number": "15"
            })

            # Should not save address
            mock_config.set_address.assert_not_called()

            # Should return error message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_empty_street(self):
        """Test with empty street parameter."""
        with patch('server.config') as mock_config:
            result = await handle_set_address({
                "city": "Дніпро",
                "street": "   ",  # Empty after strip
                "house_number": "15"
            })

            # Should not save address
            mock_config.set_address.assert_not_called()

            # Should return error message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_strips_whitespace(self):
        """Test that whitespace is stripped from inputs."""
        with patch('server.config') as mock_config:
            result = await handle_set_address({
                "city": "  Дніпро  ",
                "street": "  Князя Володимира Великого  ",
                "house_number": "  15  "
            })

            # Should save with stripped values
            mock_config.set_address.assert_called_once_with(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )


class TestCheckSchedule:
    """Test check_outage_schedule tool handler."""

    @pytest.mark.asyncio
    async def test_no_address_configured(self):
        """Test when address is not configured."""
        with patch('server.config') as mock_config:
            mock_config.get_address.return_value = None

            result = await handle_check_schedule({})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should contain error about address not configured

    @pytest.mark.asyncio
    async def test_uses_fresh_cache(self):
        """Test that fresh cache is used when available."""
        with patch('server.config') as mock_config, \
             patch('server.format_schedule_response') as mock_format:

            # Setup mock address
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Setup fresh cache (less than 1 hour old)
            mock_cache = ScheduleCache(
                actual_schedules=[
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week="Понеділок",
                        date="15.11.25",
                        start_hour=10,
                        end_hour=11,
                        outage_type=OutageType.DEFINITE
                    )
                ],
                possible_schedules=[],
                last_updated=datetime.now()  # Fresh cache
            )
            mock_config.load_schedule_cache.return_value = mock_cache
            mock_format.return_value = "Formatted schedule"

            result = await handle_check_schedule({"force_refresh": False})

            # Should use cache and not fetch
            assert len(result) == 1
            # format_schedule_response should be called with from_cache=True
            mock_format.assert_called_once()
            call_args = mock_format.call_args
            assert call_args.kwargs.get('from_cache') == True

    @pytest.mark.asyncio
    async def test_fetches_when_cache_stale(self):
        """Test that fresh data is fetched when cache is stale."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            # Setup mock address
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Setup stale cache (more than 1 hour old)
            mock_cache = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now() - timedelta(hours=2)  # Stale
            )
            mock_config.load_schedule_cache.return_value = mock_cache

            # Setup mock fetch response
            fresh_cache = ScheduleCache(
                actual_schedules=[
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week="Понеділок",
                        date="15.11.25",
                        start_hour=10,
                        end_hour=11,
                        outage_type=OutageType.DEFINITE
                    )
                ],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_fetch.return_value = fresh_cache
            mock_format.return_value = "Fresh schedule"

            result = await handle_check_schedule({"force_refresh": False})

            # Should fetch fresh data
            mock_fetch.assert_called_once()
            # Should save to cache
            mock_config.save_schedule_cache.assert_called_once_with(fresh_cache)
            # format_schedule_response should be called with from_cache=False
            call_args = mock_format.call_args
            assert call_args.kwargs.get('from_cache') == False

    @pytest.mark.asyncio
    async def test_force_refresh(self):
        """Test force_refresh parameter bypasses cache."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch, \
             patch('server.format_schedule_response') as mock_format:

            # Setup mock address
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Setup fresh cache
            mock_cache = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now()  # Fresh but should be bypassed
            )
            mock_config.load_schedule_cache.return_value = mock_cache

            # Setup mock fetch response
            fresh_cache = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_fetch.return_value = fresh_cache
            mock_format.return_value = "Fresh schedule"

            result = await handle_check_schedule({"force_refresh": True})

            # Should fetch despite fresh cache
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_error_handling(self):
        """Test error handling when fetch fails."""
        with patch('server.config') as mock_config, \
             patch('server.fetch_dtek_schedule', new_callable=AsyncMock) as mock_fetch:

            # Setup mock address
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None

            # Setup fetch to raise exception
            mock_fetch.side_effect = Exception("Network error")

            result = await handle_check_schedule({})

            # Should return error message
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "Network error" in result[0].text or "помилка" in result[0].text.lower()


class TestGetNextOutage:
    """Test get_next_outage tool handler."""

    @pytest.mark.asyncio
    async def test_no_address_configured(self):
        """Test when address is not configured."""
        with patch('server.config') as mock_config:
            mock_config.get_address.return_value = None

            result = await handle_get_next_outage({})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_no_schedule_data(self):
        """Test when no schedule data in cache."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None

            result = await handle_get_next_outage({})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_empty_cache(self):
        """Test when cache exists but has no schedules."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            empty_cache = ScheduleCache(
                actual_schedules=[],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_config.load_schedule_cache.return_value = empty_cache

            result = await handle_get_next_outage({})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)


class TestGetOutagesForDay:
    """Test get_outages_for_day tool handler."""

    @pytest.mark.asyncio
    async def test_no_address_configured(self):
        """Test when address is not configured."""
        with patch('server.config') as mock_config:
            mock_config.get_address.return_value = None

            result = await handle_get_outages_for_day({"day_of_week": "Понеділок"})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_filters_by_day(self):
        """Test filtering outages by day of week."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Setup cache with multiple days
            cache = ScheduleCache(
                actual_schedules=[
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week="Понеділок",
                        date="15.11.25",
                        start_hour=10,
                        end_hour=11,
                        outage_type=OutageType.DEFINITE
                    ),
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week="Вівторок",
                        date="16.11.25",
                        start_hour=12,
                        end_hour=13,
                        outage_type=OutageType.DEFINITE
                    )
                ],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_config.load_schedule_cache.return_value = cache

            result = await handle_get_outages_for_day({
                "day_of_week": "Понеділок",
                "schedule_type": "actual"
            })

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should contain Monday data but not Tuesday
            assert "Понеділок" in result[0].text
            assert "10" in result[0].text or "10:00" in result[0].text


class TestConfigureMonitoring:
    """Test configure_monitoring tool handler."""

    @pytest.mark.asyncio
    async def test_saves_monitoring_config(self):
        """Test that monitoring configuration is saved."""
        with patch('server.config') as mock_config:
            # Mock get_monitoring to return a MonitoringConfig object
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

            # Should update monitoring config
            mock_config.update_monitoring.assert_called_once()

            # Verify the monitoring object was updated
            assert mock_monitoring.notification_before_minutes == 30
            assert mock_monitoring.enabled == True
            assert mock_monitoring.check_interval_minutes == 15

            assert len(result) == 1
            assert isinstance(result[0], TextContent)


class TestCheckUpcomingOutages:
    """Test check_upcoming_outages tool handler."""

    @pytest.mark.asyncio
    async def test_no_address_configured(self):
        """Test when address is not configured."""
        with patch('server.config') as mock_config:
            mock_config.get_address.return_value = None

            result = await handle_check_upcoming_outages({})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
