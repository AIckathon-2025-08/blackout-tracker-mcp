"""
Unit tests for calculate_charging_time tool.

Tests the charging time calculation and optimal window recommendation logic.
"""
import sys
sys.path.insert(0, 'src')

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from mcp.types import TextContent

from server import handle_calculate_charging_time
from config import Address, ScheduleCache, OutageSchedule, ScheduleType, OutageType


class TestCalculateChargingTime:
    """Test calculate_charging_time tool handler."""

    @pytest.mark.asyncio
    async def test_invalid_params_current_greater_than_target(self):
        """Test with current charge greater than target."""
        result = await handle_calculate_charging_time({
            "device_capacity_wh": 50,
            "current_charge_percent": 80,
            "target_charge_percent": 60,
            "charging_power_w": 65
        })

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid" in result[0].text.lower() or "некоректні" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_params_negative_capacity(self):
        """Test with negative capacity."""
        result = await handle_calculate_charging_time({
            "device_capacity_wh": -50,
            "current_charge_percent": 20,
            "target_charge_percent": 80,
            "charging_power_w": 65
        })

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_no_address_configured(self):
        """Test when address is not configured."""
        with patch('server.config') as mock_config:
            mock_config.get_address.return_value = None

            result = await handle_calculate_charging_time({
                "device_capacity_wh": 50,
                "current_charge_percent": 20,
                "target_charge_percent": 80,
                "charging_power_w": 65
            })

            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_no_schedule_data(self):
        """Test when no schedule data is available."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address
            mock_config.load_schedule_cache.return_value = None

            result = await handle_calculate_charging_time({
                "device_capacity_wh": 50,
                "current_charge_percent": 20,
                "target_charge_percent": 80,
                "charging_power_w": 65
            })

            assert len(result) == 1
            assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_charging_calculation_with_available_windows(self):
        """Test charging calculation with available power windows."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Create schedule with some outages
            now = datetime.now()
            today_date = now.strftime("%d.%m.%y")
            days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
            today_day = days[now.weekday()]

            mock_cache = ScheduleCache(
                actual_schedules=[
                    # Outage from 10-12
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week=today_day,
                        date=today_date,
                        start_hour=10,
                        end_hour=12,
                        outage_type=OutageType.DEFINITE
                    ),
                    # Outage from 15-17
                    OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week=today_day,
                        date=today_date,
                        start_hour=15,
                        end_hour=17,
                        outage_type=OutageType.DEFINITE
                    ),
                ],
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_config.load_schedule_cache.return_value = mock_cache

            # Test charging calculation
            # Device: 50Wh capacity, charge from 20% to 80% (30Wh needed)
            # Charger: 65W -> 30Wh / 65W = 0.46 hours (about 28 minutes)
            result = await handle_calculate_charging_time({
                "device_capacity_wh": 50,
                "current_charge_percent": 20,
                "target_charge_percent": 80,
                "charging_power_w": 65
            })

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should contain charging time and windows
            assert "0h 27m" in result[0].text or "0h 28m" in result[0].text or "0г 27хв" in result[0].text or "0г 28хв" in result[0].text

    @pytest.mark.asyncio
    async def test_insufficient_power_window(self):
        """Test when no window is long enough for charging."""
        with patch('server.config') as mock_config:
            mock_address = Address(
                city="Дніпро",
                street="Князя Володимира Великого",
                house_number="15"
            )
            mock_config.get_address.return_value = mock_address

            # Create schedule with many short outages (no long power windows)
            now = datetime.now()
            today_date = now.strftime("%d.%m.%y")
            days = ['Понеділок', 'Вівторок', 'Середа', 'Четвер', 'П\'ятниця', 'Субота', 'Неділя']
            today_day = days[now.weekday()]

            # Create outages every 2 hours (leaving only 1-hour windows)
            outages = []
            for hour in range(0, 24, 2):
                if hour < 23:
                    outages.append(OutageSchedule(
                        schedule_type=ScheduleType.ACTUAL,
                        day_of_week=today_day,
                        date=today_date,
                        start_hour=hour,
                        end_hour=hour + 1,
                        outage_type=OutageType.DEFINITE
                    ))

            mock_cache = ScheduleCache(
                actual_schedules=outages,
                possible_schedules=[],
                last_updated=datetime.now()
            )
            mock_config.load_schedule_cache.return_value = mock_cache

            # Test with large battery that needs 5 hours to charge
            # Device: 300Wh capacity, charge from 0% to 100% (300Wh needed)
            # Charger: 60W -> 300Wh / 60W = 5 hours
            result = await handle_calculate_charging_time({
                "device_capacity_wh": 300,
                "current_charge_percent": 0,
                "target_charge_percent": 100,
                "charging_power_w": 60
            })

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should contain warning about insufficient time
            assert "WARNING" in result[0].text or "УВАГА" in result[0].text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
