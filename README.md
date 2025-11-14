# Electricity Shutdowns MCP Server

An MCP server for monitoring electricity outage schedules in Ukraine (DTEK Dnipro Electric Networks). Currently supports Dnipropetrovsk region only.

## Description

This MCP server helps track scheduled electricity outages and provides timely notifications about upcoming shutdowns. Especially useful for planning laptop charging and managing other devices during power outages.

### Key Features

- 🔍 **Schedule Checking** - Get outage schedules for your specific address
- ⏰ **Smart Notifications** - Get notified 1 hour (configurable) before outages
- 📊 **Change Detection** - Automatic schedule monitoring and change alerts
- 🔋 **Charging Calculator** - Smart calculation of optimal charging time (in development)
- 🌐 **Real-time Parsing** - Live data from DTEK website
- 💾 **Smart Caching** - 1-hour cache to reduce server load

## Requirements

- Python 3.10 or higher
- Claude Desktop or Claude Code
- Internet connection to access DTEK website
- Chromium browser (installed automatically via Playwright)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd electricity_shutdowns_mcp
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browser

```bash
playwright install chromium
```

### 5. Verify Installation

Run the validation test to ensure everything is set up correctly:

```bash
python test_mcp_server.py
```

You should see:
```
✓ ALL VALIDATIONS PASSED
```

## Claude Code Setup

There are two methods to integrate this MCP server with Claude Code/Desktop:

### Method 1: Local Development (Recommended for Testing)

This method is suitable for local development and testing.

**Step 1:** Ensure your virtual environment is activated

```bash
cd electricity_shutdowns_mcp
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

**Step 2:** If there's an `mcp.json` file in your project directory, Claude Code will automatically detect and offer to use the MCP server.

### Method 2: Global Configuration (Recommended for Daily Use)

This method is suitable for permanent use with Claude Desktop.

**Step 1:** Locate the Claude Desktop configuration file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux:** `~/.config/Claude/claude_desktop_config.json`

**Step 2:** Add the MCP server configuration:

Open `claude_desktop_config.json` and add:

```json
{
  "mcpServers": {
    "electricity-shutdowns": {
      "command": "/ABSOLUTE/PATH/TO/PROJECT/venv/bin/python",
      "args": [
        "-m",
        "src.server"
      ],
      "cwd": "/ABSOLUTE/PATH/TO/PROJECT/electricity_shutdowns_mcp",
      "env": {}
    }
  }
}
```

**Important:** Replace `/ABSOLUTE/PATH/TO/PROJECT/` with the actual absolute path to your project.

**Example for macOS:**
```json
{
  "mcpServers": {
    "electricity-shutdowns": {
      "command": "/Users/username/projects/electricity_shutdowns_mcp/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/Users/username/projects/electricity_shutdowns_mcp",
      "env": {}
    }
  }
}
```

**Step 3:** Restart Claude Desktop for changes to take effect.

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
Set my address: м. Дніпро, Просп. Миру, 4
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
You: Set my address to м. Кривий Ріг, Вешенська, 8

Claude: [Calls set_address]
✓ Address saved: м. Кривий Ріг, Вешенська, буд. 8

You: Check outage schedule

Claude: [Calls check_outage_schedule]
📍 Address: м. Кривий Ріг, Вешенська, буд. 8
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
~/.config/electricity_shutdowns_mcp/
├── config.json          # Address and monitoring settings
└── schedule_cache.json  # Outage schedules cache
```

### Cache Format (kept for 1 hour):
- `actual_schedules` - Accurate schedules for today/tomorrow
- `possible_schedules` - Weekly forecast schedules
- `last_updated` - Last update timestamp

## Project Structure

```
electricity_shutdowns_mcp/
├── src/
│   ├── server.py           # Main MCP server
│   ├── parser.py           # DTEK website parser
│   ├── scheduler.py        # Monitoring and notification logic (planned)
│   └── config.py           # Configuration and data storage
├── test_fill_form.py       # Parser test (full cycle)
├── test_visible.py         # Parser test (visible browser)
├── test_save_html.py       # Parser test (save HTML)
├── test_mcp_server.py      # MCP server validation test
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
Set address: м. Дніпро, Просп. Миру, 4
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
    "electricity-shutdowns": {
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

## License

MIT

## Authors

- Yaroslav Yenkala
- Bohdan Perchuk

## Support

For questions and suggestions, please create issues in the repository.

---

**Слава Україні!** 🇺🇦
