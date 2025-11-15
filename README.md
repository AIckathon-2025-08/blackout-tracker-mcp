# Electricity Shutdowns MCP Server

An MCP server for monitoring electricity outage schedules in Ukraine (DTEK Dnipro Electric Networks). Currently, supports Dnipropetrovsk region only.

## Table of Contents

- [Description](#description)
- [Quick Start](#quick-start-docker---recommended)
- [Usage](#usage)
- [Available Tools](#available-tools)
- [Language Support](#language-support)
- [Data Source](#data-source)
- [Configuration & Data Storage](#configuration--data-storage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Advanced Configuration](#advanced-configuration)
- [Alternative Installation Methods](#alternative-installation-methods)
- [Roadmap](#roadmap)
- [Resources](#resources)
- [Authors](#authors)

## Description

This MCP server helps track scheduled electricity outages and provides timely notifications about upcoming shutdowns. Especially useful for planning laptop charging and managing other devices during power outages.

## Demo video link to google drive:

https://drive.google.com/file/d/1RsHJWdFBvEGF-KOu3yS7BWbEXgPU-E2V/view?usp=sharing

## Screenshots

- Set address:

![img.png](screenshots/set_address.png)

- Check next electricity outage:

![img.png](screenshots/check_next_outage.png)

- Check electricity outage for specific date:
![img.png](screenshots/check_outage_for_today.png)

- Check outage for this week (possible outages):
![img.png](screenshots/check_outage_for_week.png)

- Check outage for specific day by hours:
![img.png](screenshots/check_outage_for_day.png)

- Configure monitoring (enable notifications):
![img.png](screenshots/configure_monitoring.png)

- Notification about upcoming outage:
![img.png](screenshots/upcoming_outage_notification.png)

- Calculate optimal MacBook charging time:
![img.png](screenshots/calculate_charging_time.png)

### Key Features

- 🔍 **Schedule Checking** - Get outage schedules for your specific address
- ⏰ **Automatic Notifications** - Background daemon monitors for upcoming outages
- 🤖 **Terminal Notifications** - Visual notifications in your terminal (iTerm2/Terminal.app)
- 📊 **Real-time Monitoring** - Daemon checks schedule every N minutes
- 🔋 **Smart Charging Calculator** - Automatically detects MacBook battery and calculates optimal charging time before outages
- 🌐 **Live Data** - Direct parsing from DTEK website
- 💾 **Smart Caching** - 1-hour cache to reduce load
- 🐳 **Zero Configuration** - Everything works out of the box with Docker

## Quick Start (Docker - Recommended)

**Prerequisites:**
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose (usually comes with Docker Desktop)
- For macOS: `terminal-notifier` for native notifications (`brew install terminal-notifier`)

**Installation:**

**1. Clone and build:**
```bash
git clone <repository-url>
cd blackout_tracker_mcp
docker-compose build
```

**2. Start the server:**
```bash
docker-compose up -d
```

This starts:
- `mcp-server` - Main MCP server (handles Claude requests)
- `notification-daemon` - Background notification daemon (monitors for outages)

**3. (Optional) Enable notifications and battery detection:**

If you want native macOS notifications and battery auto-detection, start the bridge scripts:
```bash
./watch_notifications.sh &     # Forwards notifications from Docker to macOS
./battery_info.sh &            # Enables battery auto-detection for charging calculator
```

**4. Configure Claude:**

Open your Claude configuration file (`code ~/.claude.json`) and add:

```json
{
  "mcpServers": {
    "blackout-tracker": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "exec",
        "-i",
        "blackout-tracker-mcp",
        "python",
        "-m",
        "src.server"
      ]
    }
  }
}
```

**Important:** Add `"mcpServers"` at the **root level** of `~/.claude.json`, **before** the `"projects"` section.

**5. Restart Claude Code/Desktop** and verify with `claude mcp list`

**That's it!** 🎉

### Verification

After connecting the MCP server, you'll see available tools:
- `set_address` - Configure your address
- `check_outage_schedule` - Check outage schedules
- `get_next_outage` - Find the next upcoming outage
- `get_outages_for_day` - Get all outages for a specific day
- `calculate_charging_time` - Calculate optimal charging time before outages (MacBook only)
- `configure_monitoring` - Configure notification settings
- `check_upcoming_outages` - Check for upcoming outages and get alerts

## Usage

### Basic Workflow

**1. Set Your Address:**

First, configure your address (note: use prefixes as they appear on DTEK website):

```
Set my address: м. Дніпро, вул. Вʼячеслава Липинського, 4
```

Claude will call `set_address` with the correct parameters.

**2. Check the Schedule:**

```
Check electricity outage schedule
```

Claude will call `check_outage_schedule` and show you the full schedule.

**3. Find Next Outage:**

```
When is the next outage?
```

Claude will call `get_next_outage` to show the nearest upcoming outage.

**4. Check Specific Day:**

```
Show all outages for Monday
```

Claude will call `get_outages_for_day` to show outages for a specific day.

**5. Enable Notifications:**

```
Enable notifications 30 minutes before outages
```

Claude will call `configure_monitoring` to set up automatic monitoring.

**6. Check Upcoming Outages:**

```
Check for upcoming outages
```

Claude will call `check_upcoming_outages` to see if any outage is approaching soon.

**7. Calculate Charging Time (MacBook only):**

```
When should I charge my MacBook before the next outage?
```

Claude will call `calculate_charging_time` to calculate optimal charging time.

### Usage Examples

#### Basic Usage

```
You: Set my address to м. Дніпро, Вʼячеслава Липинського, 4

Claude: [Calls set_address]
✓ Address saved: м. Дніпро, Вʼячеслава Липинського, 4

You: Check outage schedule

Claude: [Calls check_outage_schedule]
📍 Address: м. Дніпро, Вʼячеслава Липинського, 4
...
```

#### Advanced Usage

```
You: When is the next outage?

Claude: [Calls get_next_outage]
⏰ Next outage:
  14.11.25 Thursday, 18:00-19:00
  Type: Definite outage ✗
```

```
You: Show all outages for Monday

Claude: [Calls get_outages_for_day with day_of_week="Понеділок"]
📅 Day: Понеділок
Outages (5):
  ✗ 15.11.25 08:00-09:00 (definite)
  ...
```

```
You: Enable notifications 30 minutes before outages

Claude: [Calls configure_monitoring]
✓ Monitoring configured:
  Notifications: enabled
  Notify 30 minutes before outage
  Check interval: 60 minutes

  The notification daemon is now running automatically in Docker and will monitor your outage schedule.
```

**That's it!** The notification daemon (already running in background) will check for outages and send notifications.

```
You: Check for upcoming outages

Claude: [Calls check_upcoming_outages]
⚠️ UPCOMING OUTAGE ALERT

Power outage starting in 25 minutes!

📅 14.11.25 Thursday
⏰ 18:00-19:00
📊 Definite outage ✗

Prepare now: charge devices, save work.
```

```
You: When should I charge my MacBook before the next outage?

Claude: [Calls calculate_charging_time]
🔋 Battery Status
  • Current charge: 45%
  • Battery capacity: 80.9 Wh
  • Charging: No
  • Power consumption: 15.2W

⚡ Next outage: Today at 18:00 (in 3h 25min)

📊 Charging Recommendations:

🎯 Target: 80% (Recommended for battery health)
  ⏰ Start charging at: 16:47 (in 2h 12min)
  ⚡ Charging time needed: ~1h 13min

🔋 Target: 100% (Maximum runtime)
  ⏰ Start charging at: 16:15 (in 1h 40min)
  ⚡ Charging time needed: ~1h 45min

💡 Tips:
  • 80% charge is better for long-term battery health
  • 100% charge gives maximum runtime during outage
```

## Available Tools

### `set_address`

Configures the user's address for checking outage schedules.

**Parameters:**
- `city` (str): City with prefix (e.g., "м. Дніпро", "м. Київ")
- `street` (str): Street with prefix (e.g., "Просп. Миру", "Вул. Шевченка")
- `house_number` (str): House number (e.g., "4", "50а")

**Returns:** Confirmation of address saved

**Important:** Address is saved and used for all subsequent requests.

### `check_outage_schedule`

Checks the current outage schedule for the configured address.

**Parameters:**
- `include_possible` (bool, optional): Include weekly forecast (default: False)
- `force_refresh` (bool, optional): Force refresh data, ignoring cache (default: False)

**Returns:**
- Accurate schedule for today/tomorrow ("Графік відключень:")
- Optional: Weekly forecast ("Графік можливих відключень на тиждень:")
- Statistics by outage types
- Last update timestamp

**Caching:** Data is cached for 1 hour to speed up repeated requests.

### `get_next_outage`

Finds the next upcoming outage from the accurate schedule.

**Parameters:** None (uses configured address)

**Returns:**
- Date and day of week of next outage
- Start and end time
- Outage type (definite/first 30 min/second 30 min)

### `get_outages_for_day`

Gets all outages for a specific day of the week.

**Parameters:**
- `day_of_week` (str): Day of week in Ukrainian (Понеділок, Вівторок, Середа, Четвер, П'ятниця, Субота, Неділя)
- `schedule_type` (str, optional): Schedule type - "actual" (accurate) or "possible_week" (forecast). Default: "actual"

**Returns:** List of all outages for the specified day with times and types

### `configure_monitoring`

Configures notification and monitoring settings.

**Parameters:**
- `notification_before_minutes` (int, optional): How many minutes before outage to send notification. Default: 60
- `enabled` (bool, optional): Enable or disable monitoring notifications. Default: false
- `check_interval_minutes` (int, optional): How often to check for updates in minutes. Default: 60

**Returns:** Confirmation of monitoring settings

**Example:**
```
Configure monitoring: enable notifications 30 minutes before outages
```

### `check_upcoming_outages`

Checks for upcoming outages based on configured notification settings. Returns an alert if an outage is approaching within the notification window.

**Parameters:** None (uses configured address and monitoring settings)

**Returns:**
- Alert message if outage is approaching within notification window
- Status message if no upcoming outages
- Reminder to enable monitoring if disabled

**Example:**
```
Check for upcoming outages
```

**Note:** This tool respects the monitoring configuration set via `configure_monitoring`. Make sure monitoring is enabled and notification window is configured.

### `calculate_charging_time`

**🪄 MAGIC!** Automatically detects your MacBook battery and calculates the optimal time to start charging to reach 80% or 100% exactly when the next power outage occurs.

**Parameters:**
- `target_charge_percent` (int, optional): Target charge level (80 or 100). Default: both levels shown

**Returns:**
- Current battery status (charge %, capacity, charging state)
- Charging recommendations for 80% and 100% targets
- Exact time when to plug in your MacBook
- Estimated charging duration

**How it works:**
1. **Automatic battery detection** - Reads your MacBook battery data (no manual input needed!)
2. **Smart calculation** - Uses actual battery capacity and current charge
3. **Precise timing** - Calculates exact moment to start charging
4. **Dual recommendations** - Shows both 80% (healthier for battery) and 100% (maximum runtime)

**Prerequisites:**

**For Docker users:**
Start the battery bridge script (once per system boot):
```bash
./battery_info.sh &
```

This script collects battery data and makes it available to Docker containers. Similar to `watch_notifications.sh` for notifications.

**For native Python users:**
Battery detection works automatically - no additional setup needed!

**Supported devices:**
- MacBook Pro (all models with built-in battery)
- MacBook Air (all models with built-in battery)

**Note:** This tool only works on macOS devices with built-in batteries. It automatically detects:
- Current charge percentage
- Battery capacity (Wh)
- Charging state
- Power consumption rate

## Language Support

The MCP server supports **English** (default) and **Ukrainian** languages.

### Default Language

By default, all tool descriptions and responses are in **English**. This makes the server accessible to international users.

### Using Ukrainian Language (Optional)

To use Ukrainian language, configure it in the config file:

**1. Locate the config file:**
```bash
~/.config/blackout_tracker_mcp/config.json
```

**2. Add or modify the language setting:**
```json
{
  "language": "uk",
  "address": {
    "city": "м. Дніпро",
    "street": "вул. Вʼячеслава Липинського",
    "house_number": "4"
  }
}
```

**3. Restart the MCP server** (restart Claude Code/Desktop or Docker container)

### Commands in Both Languages

You can use natural language in either English or Ukrainian when talking to Claude. Here are examples:

#### English Commands:
```
Set my address to м. Дніпро, вул. В'ячеслава Липинського
Check electricity outage schedule
Check electricity outage schedule for today (with time when we have electricity too and summary)
When is the next outage?
Show all outages for Monday
Include possible outages for the week
Enable notifications 50 minutes before outages
Calculate charging time for nearest outage
```

#### Ukrainian Commands:
```
Встанови мою адресу: м. Дніпро, вул. Вʼячеслава Липинського, 4
Перевір графік відключень світла
Коли наступне відключення?
Покажи всі відключення на понеділок
Включи можливі відключення на тиждень
Увімкни сповіщення за 50 хвилин до відключень
Розрахуй час зарядки перед наступним відключенням
```

**Note:** The language setting only affects the **output format** (tool descriptions and responses). You can speak to Claude in any language regardless of the configured language.

## Data Source

Data is sourced from the official DTEK Dnipro Electric Networks website:
https://www.dtek-dnem.com.ua/ua/shutdowns

### Schedule Types

DTEK provides two types of schedules:

#### 1. "Графік відключень:" (Actual Schedule)
- Accurate outage schedule for today and tomorrow
- Tomorrow's data usually appears by end of day
- Used for notifications and precise planning
- Priority source for "today" requests

#### 2. "Графік можливих відключень на тиждень:" (Possible Schedule)
- Weekly forecast of possible outages
- Less precise, used for general planning
- Shown to user only when requesting specific days

### Outage Types

Different markers are used on the schedule:

- **✗** (black) - "Світла немає" - Definite outage
- **⚡** (yellow) - "Світла не буде перші 30 хв" - Outage in first 30 minutes of hour
- **⚡*** (with asterisk) - "Світла можливо не буде другі 30 хв" - Possible outage in second 30 minutes
- **Gray background** - "Можливо відключення" - Possible outage (from weekly schedule)

## Configuration & Data Storage

Configuration and cache are stored in:

```
~/.config/blackout_tracker_mcp/
├── config.json          # Address and monitoring settings
└── schedule_cache.json  # Outage schedules cache
```

### Cache Format (kept for 1 hour):
- `actual_schedules` - Accurate schedules for today/tomorrow
- `possible_schedules` - Weekly forecast schedules
- `last_updated` - Last update timestamp

## Project Structure

```
blackout_tracker_mcp/
├── src/
│   ├── server.py                # Main MCP server
│   ├── parser.py                # DTEK website parser
│   ├── battery.py               # MacBook battery auto-detection
│   ├── scheduler.py             # Monitoring and notification logic
│   ├── monitor_outages_daemon.py # Background notification daemon
│   ├── config.py                # Configuration and data storage
│   └── translations/            # i18n translations (en, uk)
├── tests/
│   ├── test_fill_form.py        # Parser test (full cycle)
│   ├── test_visible.py          # Parser test (visible browser)
│   ├── test_save_html.py        # Parser test (save HTML)
│   ├── test_mcp_server.py       # MCP server validation test
│   ├── test_apostrophe_normalization.py # Apostrophe handling test
│   └── test_i18n.py             # Internationalization test
├── battery_info.sh              # Battery bridge script (macOS → Docker)
├── watch_notifications.sh       # Notification bridge script (Docker → macOS)
├── battery_status.json          # Battery data file (auto-generated, gitignored)
├── Dockerfile                   # Docker image configuration
├── docker-compose.yml           # Docker Compose configuration
├── .dockerignore                # Docker ignore file
├── mcp.json                     # MCP configuration for Claude Code
├── requirements.txt             # Python dependencies
├── pyproject.toml               # Project metadata
├── README.md                    # This file
├── ARCHITECTURE.md              # Architecture documentation
└── TODO.md                      # Development roadmap
```

## Troubleshooting

### MCP Server Not Starting

**Solution:**
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Verify Playwright is installed: `playwright install chromium`
3. Check paths in configuration (must be absolute paths)
4. Run validation test: `python test_mcp_server.py`

### "Address not configured" Error

**Solution:**
First configure your address using `set_address`:
```
Set address: м. Дніпро, вул. Вʼячеслава Липинського, 4
```

### Parsing Error

**Solution:**
1. Ensure address is specified correctly (with prefixes: м., Просп., Вул.)
2. Check DTEK website is accessible: https://www.dtek-dnem.com.ua/ua/shutdowns
3. Try using `force_refresh: true` for forced update
4. Check if website structure changed (selectors in `parser.py` may need updating)

### MCP Server Not Detected in Claude Code

**Solution:**
1. Verify paths in configuration are correct
2. Ensure virtual environment is activated
3. Restart Claude Desktop
4. Check Claude Desktop logs for errors

### Debugging with Logs

Enable detailed logging by adding to your configuration:

```json
{
  "mcpServers": {
    "blackout-tracker": {
      "type": "stdio",
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/project",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

Logs can be viewed in Claude Desktop console (accessible through developer menu).

## Development

### Running in Development Mode

```bash
source venv/bin/activate
python -m src.server
```

The server expects input via stdio (standard input/output).

### Running Tests

**Using Docker (Recommended):**
```bash
# Run specific test
docker-compose run --rm --entrypoint python test-runner tests/test_mcp_server.py

# Run apostrophe normalization test
docker-compose run --rm --entrypoint python test-runner tests/test_apostrophe_normalization.py

# Run internationalization test
docker-compose run --rm --entrypoint python test-runner tests/test_i18n.py

# Run parser integration test
docker-compose run --rm --entrypoint python test-runner tests/test_fill_form.py
```

**Using local Python environment:**
```bash
# Activate virtual environment first
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Parser tests
python tests/test_fill_form.py           # Full cycle test
python tests/test_visible.py             # Visible browser test
python tests/test_save_html.py           # Save HTML test

# MCP server validation
python tests/test_mcp_server.py

# Apostrophe normalization test (regression test)
python tests/test_apostrophe_normalization.py

# Internationalization test
python tests/test_i18n.py
```

### Running Unit Tests (when available)

```bash
pytest tests/
```

## Advanced Configuration

### Managing Background Scripts

The bridge scripts (`watch_notifications.sh` and `battery_info.sh`) run in the background with the `&` ampersand operator.

**What is `&` (ampersand)?**
- `&` runs the script in **background** - terminal is immediately available for other commands
- Without `&`, the script runs in **foreground** - terminal is blocked until you press `Ctrl+C`
- Both scripts have infinite loops, so `&` is essential to keep your terminal usable

**Check if scripts are running:**
```bash
ps aux | grep -E "battery_info|watch_notifications" | grep -v grep
```

**Stop the scripts:**
```bash
# Stop battery bridge
pkill -f battery_info.sh

# Stop notification bridge
pkill -f watch_notifications.sh

# Stop both at once
pkill -f "battery_info.sh|watch_notifications.sh"
```

### Useful Docker Commands

```bash
# View MCP server logs
docker-compose logs -f mcp-server

# View notification daemon logs (see monitoring in action!)
docker-compose logs -f notification-daemon

# View both logs together
docker-compose logs -f

# Stop all services
docker-compose down

# Restart MCP server after code changes
docker-compose restart mcp-server

# Restart notification daemon
docker-compose restart notification-daemon

# Run tests
docker-compose --profile test run --rm test-runner
# Or run one test specifically:
docker exec -i blackout-tracker-mcp python tests/test_apostrophe_normalization.py
```

### Notification Daemon Details

The notification daemon automatically:
- Starts when you run `docker-compose up -d`
- Checks for upcoming outages every N minutes (configurable)
- Sends terminal notifications when outage is approaching
- Keeps running in background even when Claude is closed

**View daemon logs:**
```bash
docker-compose logs -f notification-daemon
```

You'll see output like:
```
[23:27:18] Check #1: Looking for upcoming outages...
✓ No upcoming outages in next 30 min
   Next check in 60 minutes
```

### macOS Native Notifications Setup

**Why Docker Can't Send macOS Notifications Directly:**

Docker containers run in an isolated environment and cannot directly access macOS system APIs, including the Notification Center. The daemon running inside Docker can only write to logs and stdout, which is why we need a bridge solution to forward notifications to your macOS Notification Center.

**Solution: Using terminal-notifier + watch script**

To receive native macOS notifications in Notification Center:

**1. Install terminal-notifier:**

```bash
brew install terminal-notifier
```

This tool allows sending notifications to macOS Notification Center from the command line.

**2. Run the notification watch script:**

The `watch_notifications.sh` script monitors Docker daemon logs and forwards notifications to macOS:

```bash
./watch_notifications.sh &
```

This will:
- Monitor the `blackout-notifier` container logs in real-time
- Detect when the daemon sends notifications (by watching for "Notification sent at HH:MM:SS")
- Send native macOS notifications via terminal-notifier
- Send only ONE notification per outage (no duplicates)
- Run in background (thanks to `&`) - your terminal remains usable

To stop watching:
```bash
pkill -f watch_notifications.sh
```

**3. OPTIONAL: Automatic startup on system login (LaunchAgent):**

To have notifications start automatically when you log in to macOS:

**Create LaunchAgent plist file:**
```bash
mkdir -p ~/Library/LaunchAgents
```

Create `~/Library/LaunchAgents/com.blackout.notifier.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.blackout.notifier</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/ABSOLUTE/PATH/TO/PROJECT/watch_notifications.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/blackout-notifier-watch.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/blackout-notifier-watch-error.log</string>
    <key>WorkingDirectory</key>
    <string>/ABSOLUTE/PATH/TO/PROJECT</string>
</dict>
</plist>
```

**Important:** Replace `/ABSOLUTE/PATH/TO/PROJECT` with your actual project path.

**Load the LaunchAgent:**
```bash
launchctl load ~/Library/LaunchAgents/com.blackout.notifier.plist
```

**Verify it's running:**
```bash
launchctl list | grep blackout
```

**Stop the LaunchAgent (if needed):**
```bash
launchctl unload ~/Library/LaunchAgents/com.blackout.notifier.plist
```

**View logs:**
```bash
tail -f /tmp/blackout-notifier-watch.log
```

**How It Works:**

1. **Daemon** (in Docker) checks for outages and writes "Notification sent at HH:MM:SS" to logs
2. **Watch script** (on macOS host) monitors Docker logs via `docker logs -f`
3. **Script detects** new notification by timestamp (no duplicates)
4. **terminal-notifier** sends native macOS notification with sound

**Notification Details:**
- **Title**: "⚡ ВІДКЛЮЧЕННЯ СВІТЛА"
- **Subtitle**: "In $minutes minutes | Через $minutes хвилин"
- **Message**: "⏰ Prepare now: charge devices, save work! ⏰ Підготуйтеся: зарядіть пристрої, збережіть роботу!"
- **Sound**: "Sosumi"
- **Grouped**: All notifications grouped as "power-outage" (only most recent visible)

**Important Notes:**
- Only ONE notification per outage is sent (the watch script prevents duplicates by tracking timestamps)
- Notifications arrive a few seconds after the daemon detects the outage
- Make sure Docker containers are running: `docker-compose up -d`
- The daemon must have monitoring enabled (see usage examples above)

## Alternative Installation Methods

### Local Python Environment (Non-Docker)

**Best for:** Development, testing, debugging

**Prerequisites:**
- Python 3.11+ installed
- Internet connection to access DTEK website

**Step-by-step setup:**

**1. Clone the repository:**
```bash
git clone <repository-url>
cd blackout_tracker_mcp
```

**2. Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**3. Install dependencies:**
```bash
pip install -r requirements.txt
```

**4. Install Playwright browser:**
```bash
playwright install chromium
```

**5. Verify installation:**
```bash
python tests/test_mcp_server.py
```

You should see: `✓ ALL VALIDATIONS PASSED`

**6. Configure Claude:**

Open your Claude configuration file (`code ~/.claude.json`) and add:

```json
{
  "mcpServers": {
    "blackout-tracker": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/PROJECT/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/ABSOLUTE/PATH/TO/PROJECT",
      "env": {}
    }
  }
}
```

**Important:**
- Replace `/ABSOLUTE/PATH/TO/PROJECT/` with the actual path to your project.
- Add `"mcpServers"` at the **root level** of `~/.claude.json`, **before** the `"projects"` section (not inside it). This makes the MCP server available globally across all projects.

**How to find your absolute path:**
```bash
cd blackout_tracker_mcp
pwd  # This shows your absolute path
```

**Example for macOS/Linux:**
```json
{
  "mcpServers": {
    "blackout-tracker": {
      "type": "stdio",
      "command": "/Users/john/projects/blackout_tracker_mcp/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/Users/john/projects/blackout_tracker_mcp",
      "env": {}
    }
  }
}
```

**Example for Windows:**
```json
{
  "mcpServers": {
    "blackout-tracker": {
      "type": "stdio",
      "command": "C:\\Users\\john\\projects\\blackout_tracker_mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:\\Users\\john\\projects\\blackout_tracker_mcp",
      "env": {}
    }
  }
}
```

**7. Restart Claude Code/Desktop**

### Using mcp.json (Quick Testing)

If there's an `mcp.json` file in your project directory, Claude Code will automatically detect and offer to use the MCP server when you open the project folder.

This is the fastest way to test during development.

## Roadmap

- [x] Basic DTEK website parsing
- [x] Core MCP tools
- [x] Claude Code integration
- [x] Internationalization (English + Ukrainian)
- [x] Docker containerization
- [x] Automatic monitoring and notifications (Phase 5)
- [x] Smart charging time calculator with auto-detection (Phase 9)
- [ ] Multiple addresses support (Phase 9)
- [ ] Schedule change history (Phase 9)

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Code Documentation](https://docs.claude.com/en/docs/claude-code)
- [DTEK Website](https://www.dtek-dnem.com.ua/ua/shutdowns)
- [Architecture Documentation](ARCHITECTURE.md)

## Authors

- Yaroslav Yenkala
- Bohdan Perchuk

## Support

For questions and suggestions, please create issues in the repository.
