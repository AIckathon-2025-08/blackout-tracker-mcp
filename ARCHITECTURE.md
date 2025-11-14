# Architecture of Electricity Shutdowns MCP Server

## System Overview

MCP server for monitoring electricity outage schedules from DTEK Dnipro Electric Networks.

## Data Structure

### Two Types of Schedules

The system works with two types of schedules from the DTEK website:

#### 1. Accurate Schedule (ACTUAL Schedule)
**Source:** Table "Графік відключень:"

**Characteristics:**
- Accurate outages for today and tomorrow
- Tomorrow's data appears closer to end of day
- Used for notifications
- Priority source for "today" requests

**Table Structure:**
```
Date: "на сьогодні 14.11.25" / "на завтра 15.11.25"
Time intervals: 00-01, 01-02, ..., 23-24
Symbols:
  ✗ (black) - definite outage
  ⚡ (yellow) - outage first 30 min
  ⚡ (with asterisk) - possible outage second 30 min
```

#### 2. Weekly Forecast (POSSIBLE_WEEK Schedule)
**Source:** Table "Графік можливих відключень на тиждень:"

**Characteristics:**
- Forecast for all days of the week
- Less accurate
- Used for general planning
- Shown only when requesting specific day of week

**Table Structure:**
```
Days of week: Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя
Time intervals: 00-01, 01-02, ..., 23-24
Symbols:
  ✗ - possible outage
  ⚡ - possible outage (various types)
  Gray background - probable outage
```

## Data Models

### Address
```python
class Address:
    city: str              # "м. Дніпро"
    street: str            # "Вʼячеслава Липинського" (with prefix from autocomplete)
    house_number: str      # "4"
```

### OutageSchedule
```python
class OutageSchedule:
    schedule_type: str     # "actual" or "possible_week"
    day_of_week: str       # "Понеділок", "Вівторок", ...
    date: Optional[str]    # "14.11.25" (only for actual)
    start_hour: int        # 0-23
    end_hour: int          # 1-24
    outage_type: str       # "definite", "first_30min", "second_30min", "possible"
    fetched_at: datetime
```

### ScheduleCache
```python
class ScheduleCache:
    actual_schedules: list[OutageSchedule]    # Accurate schedule
    possible_schedules: list[OutageSchedule]  # Weekly forecast
    last_updated: datetime
```

## System Components

### 1. Parser (parser.py)
Responsible for parsing the DTEK website.

**Main Functions:**
- `fill_form(city, street, house_number)` - fill address form
- `parse_actual_schedule()` - parse "Графік відключень:" table
- `parse_possible_schedule()` - parse "Графік можливих відключень на тиждень:" table
- `detect_outage_type(cell)` - determine outage type by icon/color

**Technologies:**
- Playwright for JS page rendering
- BeautifulSoup for HTML parsing

### 2. Config (config.py)
Configuration management and data storage.

**Responsibilities:**
- Store user address
- Monitor configuration
- Cache schedules (both types separately)
- Load/save to JSON

**Files:**
- `~/.config/blackout_tracker_mcp/config.json` - configuration
- `~/.config/blackout_tracker_mcp/schedule_cache.json` - schedule cache

### 3. Scheduler (scheduler.py)
Monitoring and notification logic.

**Responsibilities:**
- Periodic checking of accurate schedule
- Comparison with previous version (change detection)
- Calculate time until next outage
- Generate notifications N minutes before

**IMPORTANT:** Notifications work only with accurate schedule (ACTUAL), not with forecast!

### 4. Server (server.py)
Main MCP server.

**MCP Tools:**

#### `set_address`
```python
Parameters:
  city: str
  street: str
  house_number: str

Returns:
  - success: bool
  - message: str
```

#### `check_outage_schedule`
```python
Parameters:
  include_possible: bool = False
  force_refresh: bool = False

Returns:
  - actual_schedules: list[OutageSchedule]
  - possible_schedules: list[OutageSchedule] (if include_possible=True)
```

#### `get_next_outage`
```python
Returns:
  - next_outage: OutageSchedule (from accurate schedule)
  - time_until: str (time until outage)
```

#### `get_outages_for_day`
```python
Parameters:
  day_of_week: str (Понеділок, Вівторок, ...)
  schedule_type: str = "actual"

Returns:
  - outages: list[OutageSchedule]
```

#### `configure_monitoring`
```python
Parameters:
  check_interval_minutes: int
  notification_before_minutes: int
  enabled: bool

Returns:
  - success: bool
  - config: MonitoringConfig
```

## Data Flow

### 1. Check Schedule
```
User Request → MCP Tool → Parser → DTEK Website
                ↓
         Parse HTML Tables
                ↓
    actual_schedules + possible_schedules
                ↓
         Save to Cache
                ↓
         Return to User
```

### 2. Monitoring and Notifications
```
Scheduler (every N minutes)
    ↓
Fetch ACTUAL schedule from Parser
    ↓
Compare with cached version
    ↓
If changed → Notify user
    ↓
Check time until next outage
    ↓
If < notification_time → Alert user
```

## Usage Examples

### Configure Address
```
Claude: Set address: м. Дніпро, вул. Вʼячеслава Липинського, буд. 4
→ Calls set_address() → saves to config
```

### Check for Today
```
User: When will power be out today?
Claude: Calls get_next_outage()
→ Returns nearest outage from ACTUAL schedule
```

### Weekly Forecast
```
User: What are possible outages on Wednesday?
Claude: Calls get_outages_for_day(day_of_week="Середа", schedule_type="possible_week")
→ Returns data from POSSIBLE_WEEK schedule
```

## Security and Error Handling

### Possible Errors:
1. DTEK website unavailable
2. HTML structure changed
3. Address not found in DTEK database
4. Playwright cannot start

### Handling:
- Fallback to cached data
- Notify user about problem
- Error logging
- Graceful degradation

## Future Improvements

1. **Charging Time Calculation**
   - Determine time until outage
   - Calculate when to start charging (to reach 100%)

2. **Support for Other Energy Companies**
   - DTEK Kyiv Electric Networks
   - DTEK Odesa Electric Networks
   - Other operators

3. **Schedule Change History**
   - Save all schedule versions
   - Analyze change frequency
   - Predict changes

4. **Calendar Integration**
   - Export to Google Calendar
   - iCal format

## Technology Stack

- **Python 3.10+** - Main language
- **Playwright** - Browser automation and JS rendering
- **BeautifulSoup4** - HTML parsing
- **MCP SDK** - Model Context Protocol implementation
- **Pydantic** - Data validation and models
- **Docker** - Containerization
- **pytest** - Testing (planned)

## Performance Considerations

### Caching Strategy
- Cache lifetime: 1 hour
- Separate caches for ACTUAL and POSSIBLE_WEEK
- Force refresh option available

### Rate Limiting
- Avoid excessive requests to DTEK website
- Use cached data when possible
- Implement exponential backoff on errors

### Resource Management
- Playwright browser cleanup
- Connection pooling
- Memory-efficient data structures
