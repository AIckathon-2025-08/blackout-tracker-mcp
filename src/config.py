"""
Configuration and data storage for Electricity Shutdowns MCP Server.
"""
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class Address(BaseModel):
    """User address information."""
    city: str  # e.g., "м. Дніпро"
    street: str  # e.g., "Просп. Миру", "Вул. Миру" (with prefix from autocomplete)
    house_number: str  # e.g., "4", "50а"

    def to_string(self) -> str:
        """Convert address to readable string."""
        return f"{self.city}, {self.street}, буд. {self.house_number}"


class MonitoringConfig(BaseModel):
    """Monitoring configuration."""
    check_interval_minutes: int = Field(default=60, description="Interval for checking schedule updates (in minutes)")
    notification_before_minutes: int = Field(default=60, description="How many minutes before outage to notify")
    enabled: bool = Field(default=False, description="Whether monitoring is enabled")


class OutageType:
    """Types of outages from DTEK schedule."""
    DEFINITE = "definite"  # ✗ (black) - Світла немає (точне відключення)
    FIRST_30_MIN = "first_30min"  # ⚡ (yellow) - Світла не буде перші 30 хв
    SECOND_30_MIN = "second_30min"  # ⚡ (with star) - Світла можливо не буде другі 30 хв
    POSSIBLE = "possible"  # Gray background - Можливо відключення (з таблиці "можливих відключень")


class ScheduleType:
    """Types of schedule tables from DTEK."""
    ACTUAL = "actual"  # "Графік відключень:" - точний графік на сьогодні/завтра
    POSSIBLE_WEEK = "possible_week"  # "Графік можливих відключень на тиждень:" - прогноз на тиждень


class OutageSchedule(BaseModel):
    """Outage schedule data."""
    schedule_type: str  # ScheduleType.ACTUAL or ScheduleType.POSSIBLE_WEEK
    day_of_week: str  # Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
    date: Optional[str] = None  # For actual schedule: "14.11.25", "15.11.25"
    start_hour: int  # 0-23
    end_hour: int  # 1-24
    outage_type: str  # One of OutageType values
    fetched_at: datetime = Field(default_factory=datetime.now)

    def __str__(self) -> str:
        time_str = f"{self.start_hour:02d}:00-{self.end_hour:02d}:00"
        date_part = f"{self.date} " if self.date else ""
        schedule_marker = "[ТОЧНО]" if self.schedule_type == ScheduleType.ACTUAL else "[МОЖЛИВО]"
        return f"{schedule_marker} {date_part}{self.day_of_week} {time_str} ({self.outage_type})"


class ScheduleCache(BaseModel):
    """Complete schedule cache with both actual and possible schedules."""
    actual_schedules: list[OutageSchedule] = Field(default_factory=list)
    possible_schedules: list[OutageSchedule] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class Config:
    """Main configuration manager."""

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize configuration manager."""
        if config_dir is None:
            # Use ~/.config/electricity_shutdowns_mcp by default
            config_dir = Path.home() / ".config" / "electricity_shutdowns_mcp"

        self.config_dir = config_dir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = self.config_dir / "config.json"
        self.cache_file = self.config_dir / "schedule_cache.json"

        self._load_config()

    def _load_config(self):
        """Load configuration from file."""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.address = Address(**data.get('address', {})) if data.get('address') else None
                self.monitoring = MonitoringConfig(**data.get('monitoring', {}))
                self.language = data.get('language', 'uk')  # Default to Ukrainian
        else:
            self.address = None
            self.monitoring = MonitoringConfig()
            self.language = 'uk'  # Default to Ukrainian

    def _save_config(self):
        """Save configuration to file."""
        data = {
            'address': self.address.model_dump() if self.address else None,
            'monitoring': self.monitoring.model_dump(),
            'language': self.language
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_address(self, city: str, street: str, house_number: str):
        """Set user address."""
        self.address = Address(
            city=city,
            street=street,
            house_number=house_number
        )
        self._save_config()

    def get_address(self) -> Optional[Address]:
        """Get configured address."""
        return self.address

    def update_monitoring(self, **kwargs):
        """Update monitoring configuration."""
        for key, value in kwargs.items():
            if hasattr(self.monitoring, key):
                setattr(self.monitoring, key, value)
        self._save_config()

    def get_monitoring(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self.monitoring

    def save_schedule_cache(self, schedule_cache: ScheduleCache):
        """Save complete schedule to cache."""
        data = schedule_cache.model_dump(mode='json')
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_schedule_cache(self) -> Optional[ScheduleCache]:
        """Load schedule from cache."""
        if not self.cache_file.exists():
            return None

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return ScheduleCache(**data)
        except Exception:
            return None

    def set_language(self, language: str):
        """
        Set interface language.

        Args:
            language: Language code ('en' or 'uk')
        """
        if language in ['en', 'uk']:
            self.language = language
            self._save_config()

    def get_language(self) -> str:
        """
        Get current interface language.

        Returns:
            Language code ('en' or 'uk')
        """
        return self.language


# Global config instance
config = Config()
