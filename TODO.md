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
- [x] Implement tool: `configure_monitoring`

## Phase 5: Monitoring and Notification Logic
- [ ] Implement periodic checking of accurate schedule (ACTUAL)
- [ ] Detect accurate schedule changes (comparison with previous version)
- [ ] Notification logic N minutes before outage (for accurate schedule only)
- [ ] Format notifications with outage type indication

## Phase 6: Claude Code Integration ✅ COMPLETED
- [x] Create configuration file for Claude Code (mcp.json)
- [x] Create detailed setup documentation

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

## Phase 8: Internationalization (i18n) ✅ COMPLETED
- [x] Add English language support. Will support 2 languages: Ukrainian and English
- [x] Create translation files (en.json, uk.json)
- [x] Create i18n module (i18n.py) with translation helper functions
- [x] Add language selection support in configuration (config.py)
- [x] Translate README and documentation to English
- [x] Translate TODO.md to English
- [x] Translate ARCHITECTURE.md to English
- [x] Add i18n import and basic structure to server.py
- [x] Full server.py message localization
  - [x] Localized list_tools() - all tool descriptions and parameter descriptions
  - [x] Localized handle_set_address() - all messages
  - [x] Localized handle_check_schedule() - all messages
  - [x] Localized handle_get_next_outage() - all messages
  - [x] Localized handle_get_outages_for_day() - all messages
  - [x] Localized format_schedule_response() - all labels and messages
- [x] Add Ukrainian command examples to README
- [x] Docker image rebuilt with i18n changes
- [x] Testing in different languages (test_i18n.py - all tests passed)
  - [x] English translations test
  - [x] Ukrainian translations test
  - [x] Translation completeness test
- [ ] Auto-detection of language (future enhancement)
- [ ] Display all request options in both languages in MCP help (future enhancement)

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

## Testing ✅ COMPLETED
- [x] Manual parser tests (test_fill_form.py, test_visible.py, test_save_html.py)
- [x] Testing on real addresses (Dnipro, Kryvyi Rih)
- [x] MCP server validation test (test_mcp_server.py)
- [x] Apostrophe normalization test (test_apostrophe_normalization.py) - regression test for Unicode apostrophe bug
- [x] Internationalization test (test_i18n.py) - tests English, Ukrainian translations and completeness
- [x] Unit tests for parser (pytest) - test_parser_unit.py with 14 tests covering _detect_outage_type_from_class, _parse_actual_schedule, _parse_possible_schedule
- [x] Tests for MCP tools - test_mcp_tools.py with 16 tests covering all 6 MCP tools (set_address, check_outage_schedule, get_next_outage, get_outages_for_day, configure_monitoring, check_upcoming_outages)
- [x] End-to-end testing - test_e2e.py with 9 workflow tests (happy path, cache behavior, error recovery, day filtering, monitoring, include_possible parameter, stale cache)

