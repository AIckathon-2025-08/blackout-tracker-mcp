# TODO: Electricity Shutdowns MCP Server

## Phase 1: Research and Preparation ✅ COMPLETED
- [x] Research DTEK website (https://www.dtek-dnem.com.ua/ua/shutdowns)
  - [x] Study form structure (custom autocomplete with IDs: cityautocomplete-list, streetautocomplete-list, house_numautocomplete-list)
  - [x] Understand request formation (form filling via Playwright)
  - [x] Research schedule table structure (div.discon-fact-table and div.discon-schedule-table)
  - [x] Check API availability (no API available, web scraping only)
- [x] Determine dependencies and libraries (Playwright, BeautifulSoup, MCP SDK)
- [x] Create project structure

## Phase 2: Environment Setup ✅ COMPLETED
- [x] Create pyproject.toml / requirements.txt
- [x] Set up Python virtual environment
- [x] Install MCP SDK (`mcp`)
- [x] Install parsing libraries (playwright, beautifulsoup4, lxml)
- [x] Create basic file structure (src/parser.py, src/config.py)

## Phase 3: DTEK Website Parser ✅ COMPLETED
- [x] Implement form filling function (city, street, house number)
  - [x] Close warning modal window
  - [x] Fill city field with autocomplete selection
  - [x] Fill street field with autocomplete selection
  - [x] Fill house number with autocomplete selection
  - [x] Wait for next field activation after selection
- [x] Implement parsing of "Графік відключень:" table (accurate schedule for today/tomorrow)
  - [x] Parse date and day of week from div.dates
  - [x] Parse time intervals (hours) from thead
  - [x] Determine outage type by CSS classes (cell-scheduled, cell-first-half, cell-second-half)
- [x] Implement parsing of "Графік можливих відключень на тиждень:" table (forecast)
  - [x] Parse days of week from first tbody column
  - [x] Parse time intervals from thead
  - [x] Determine possible outage type (cell-scheduled-maybe)
- [x] Structure data (ScheduleType.ACTUAL vs POSSIBLE_WEEK)
- [x] Add error handling (try-catch blocks, fallback logic)
- [x] Parser testing (tested on real addresses: Dnipro and Kryvyi Rih)

## Phase 4: Main MCP Server ✅ COMPLETED
- [x] Implement configuration (config.py with Address, MonitoringConfig, OutageSchedule, ScheduleCache)
- [x] Add data storage (cache for both schedule types in JSON)
- [x] Initialize MCP server (server.py)
- [x] Implement tool: `check_outage_schedule` (check accurate schedule + optionally forecast)
- [x] Implement tool: `get_next_outage` (next outage from accurate schedule)
- [x] Implement tool: `get_outages_for_day` (outages for specific day)
- [x] Implement tool: `set_address` (configure user address)
- [x] Create configuration files (mcp.json, CLAUDE_CODE_SETUP.md)
- [x] Add validation test (test_mcp_server.py)
- [ ] Implement tool: `configure_monitoring` (monitoring configuration - optional for later)

## Phase 5: Monitoring and Notification Logic
- [ ] Implement periodic checking of accurate schedule (ACTUAL)
- [ ] Detect accurate schedule changes (comparison with previous version)
- [ ] Notification logic N minutes before outage (for accurate schedule only)
- [ ] Format notifications with outage type indication

## Phase 6: Claude Code Integration 🔄 IN PROGRESS (NEXT PRIORITY!)
- [x] Create configuration file for Claude Code (mcp.json)
- [x] Create detailed setup documentation (CLAUDE_CODE_SETUP.md)
- [ ] **Test launch via Claude Code**
- [ ] **Test all tools in Claude Code**
- [ ] Debug and fixes as needed

## Phase 7: Repository Dockerization ✅ COMPLETED
- [x] Create Dockerfile for MCP server containerization
- [x] Configure docker-compose for local development and testing
- [x] Create .dockerignore for image optimization
- [x] Update documentation with Docker launch instructions
- [x] Test Docker image (validation tests passed successfully)
- [x] Add Docker configuration for Claude Desktop
- [x] Create profiles for different testing scenarios
- [x] Fix Playwright browser installation for non-root user (mcpuser)
- [x] Add PYTHONPATH environment variable for proper module resolution

## Phase 8: Internationalization (i18n) ✅ PARTIALLY COMPLETED
- [x] Add English language support. Will support 2 languages: Ukrainian and English
- [x] Create translation files (en.json, uk.json)
- [x] Create i18n module (i18n.py) with translation helper functions
- [x] Add language selection support in configuration (config.py)
- [x] Translate README and documentation to English
- [x] Translate TODO.md to English
- [x] Translate ARCHITECTURE.md to English
- [x] Add i18n import and basic structure to server.py
- [ ] Full server.py message localization (can be done in separate commit)
- [ ] Testing in different languages
- [ ] Auto-detection of language
- [ ] Display all request options in both languages in MCP help

## Phase 9: Additional Features
- [ ] Calculate optimal charging time (tool: `calculate_charging_time`)
- [ ] Configurable check intervals
- [ ] Multiple addresses support
- [ ] Schedule change history

## Documentation ✅ COMPLETED
- [x] README.md with complete installation and setup instructions (in English)
- [x] ARCHITECTURE.md with project structure description
- [x] Description of schedule types and outages
- [x] Usage examples for all tools
- [x] Detailed Troubleshooting section
- [x] Claude Code setup instructions (two methods)
- [x] Merge CLAUDE_CODE_SETUP.md into README.md
- [x] Docker setup documentation

## Testing ✅ PARTIALLY COMPLETED
- [x] Manual parser tests (test_fill_form.py, test_visible.py, test_save_html.py)
- [x] Testing on real addresses (Dnipro, Kryvyi Rih)
- [x] MCP server validation test (test_mcp_server.py)
- [x] Apostrophe normalization test (test_apostrophe_normalization.py) - regression test for Unicode apostrophe bug
- [ ] Unit tests for parser (pytest)
- [ ] Tests for MCP tools
- [ ] End-to-end testing

