# Electricity Shutdowns MCP Server

An MCP server for monitoring electricity outage schedules in Ukraine (DTEK Dnipro Electric Networks). Currently, supports Dnipropetrovsk region only.

## Table of Contents

- [Description](#description)
- [Claude Code Setup](#claude-code-setup)
  - [Option A: Using Docker (Recommended)](#option-a-using-docker-recommended-for-daily-use)
  - [Option B: Using Local Python Environment](#option-b-using-local-python-environment-for-development)
  - [Alternative: Using mcp.json](#alternative-using-mcpjson-quick-testing)
- [Usage](#usage)
  - [Basic Workflow](#basic-workflow)
  - [Usage Examples](#usage-examples)
- [Available Tools](#available-tools)
  - [set_address](#set_address)
  - [check_outage_schedule](#check_outage_schedule)
  - [get_next_outage](#get_next_outage)
  - [get_outages_for_day](#get_outages_for_day)
- [Data Source](#data-source)
  - [Schedule Types](#schedule-types)
  - [Outage Types](#outage-types)
- [Configuration & Data Storage](#configuration--data-storage)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Roadmap](#roadmap)
- [Resources](#resources)
- [Authors](#authors)
- [Support](#support)

## Description

This MCP server helps track scheduled electricity outages and provides timely notifications about upcoming shutdowns. Especially useful for planning laptop charging and managing other devices during power outages.

### Key Features

- 🔍 **Schedule Checking** - Get outage schedules for your specific address
- ⏰ **Smart Notifications** - Get notified 1 hour (configurable) before outages
- 📊 **Change Detection** - Automatic schedule monitoring and change alerts
- 🔋 **Charging Calculator** - Smart calculation of optimal charging time (in development)
- 🌐 **Real-time Parsing** - Live data from DTEK website
- 💾 **Smart Caching** - 1-hour cache to reduce server load

## Claude Code Setup

Choose one of the following approaches based on your needs:

### Option A: Using Docker (Recommended for Daily Use)

**Best for:** Production/home use, no need to manage Python dependencies

**Prerequisites:**
- Docker installed ([Get Docker](https://docs.docker.com/get-docker/))
- Docker Compose (usually comes with Docker Desktop)

**Step-by-step setup:**

**1. Clone the repository:**
```bash
git clone <repository-url>
cd blackout_tracker_mcp
```

**2. Build the Docker image:**
```bash
docker-compose build
```

**3. Start the MCP server:**
```bash
docker-compose up -d mcp-server
```

**4. Configure Claude:**

Open your Claude configuration file (`code ~/.claude.json`) and add:

```json
{
  "mcpServers": {
    "blackout-tracker": {
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

**5. Restart Claude Code/Desktop**

**That's it!** No absolute paths needed. Docker handles everything.

**Useful Docker commands:**
```bash
# View logs
docker-compose logs -f mcp-server

# Stop the server
docker-compose down

# Restart after code changes
docker-compose restart mcp-server

# Run tests
docker-compose --profile test run --rm test-runner
```

---

### Option B: Using Local Python Environment (For Development)

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
      "command": "/ABSOLUTE/PATH/TO/PROJECT/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/ABSOLUTE/PATH/TO/PROJECT",
      "env": {}
    }
  }
}
```

**Important:** Replace `/ABSOLUTE/PATH/TO/PROJECT/` with the actual path to your project.

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
      "command": "C:\\Users\\john\\projects\\blackout_tracker_mcp\\venv\\Scripts\\python.exe",
      "args": ["-m", "src.server"],
      "cwd": "C:\\Users\\john\\projects\\blackout_tracker_mcp",
      "env": {}
    }
  }
}
```

**7. Restart Claude Code/Desktop**

---

### Alternative: Using mcp.json (Quick Testing)

If there's an `mcp.json` file in your project directory, Claude Code will automatically detect and offer to use the MCP server when you open the project folder.

This is the fastest way to test during development.

### Verification

After connecting the MCP server, you'll see available tools:
- `set_address` - Configure your address
- `check_outage_schedule` - Check outage schedules
- `get_next_outage` - Find the next upcoming outage
- `get_outages_for_day` - Get all outages for a specific day

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
When is the next outage?
```

Claude will call `check_outage_schedule` and show you the results.

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
│   ├── server.py           # Main MCP server
│   ├── parser.py           # DTEK website parser
│   ├── scheduler.py        # Monitoring and notification logic (planned)
│   └── config.py           # Configuration and data storage
├── test_fill_form.py       # Parser test (full cycle)
├── test_visible.py         # Parser test (visible browser)
├── test_save_html.py       # Parser test (save HTML)
├── test_mcp_server.py      # MCP server validation test
├── Dockerfile              # Docker image configuration
├── docker-compose.yml      # Docker Compose configuration
├── .dockerignore           # Docker ignore file
├── mcp.json                # MCP configuration for Claude Code
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata
├── README.md               # This file
├── ARCHITECTURE.md         # Architecture documentation
└── TODO.md                 # Development roadmap
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

**Parser tests:**
```bash
# Full cycle test
python test_fill_form.py

# Visible browser test
python test_visible.py

# Save HTML test
python test_save_html.py
```

**MCP server validation:**
```bash
python test_mcp_server.py
```

### Running Unit Tests (when available)

```bash
pytest tests/
```

## Roadmap

- [x] Basic DTEK website parsing
- [x] Core MCP tools
- [x] Claude Code integration
- [ ] Automatic monitoring and notifications (Phase 5)
- [ ] Internationalization (English + Ukrainian) (Phase 7)
- [ ] Smart charging time calculator (Phase 8)
- [ ] Multiple addresses support (Phase 8)
- [ ] Schedule change history (Phase 8)

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
