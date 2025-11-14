"""
Test script to verify MCP server structure and imports.
This validates that the server is properly configured without actually running it.
"""
import sys
import inspect
sys.path.insert(0, 'src')


def test_imports():
    """Test that all imports work correctly."""
    print("=" * 60)
    print("Testing MCP Server - Imports")
    print("=" * 60)

    try:
        from server import app
        from config import config
        from parser import fetch_dtek_schedule
        print("\n✓ All imports successful")
        return True, app
    except Exception as e:
        print(f"\n✗ Import error: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_server_structure(app):
    """Test that server has required handlers."""
    print("\n" + "=" * 60)
    print("Testing MCP Server - Structure")
    print("=" * 60)

    # Check that app is a Server instance
    if not app:
        print("\n✗ Server app is None")
        return False

    print(f"\n✓ Server app created: {type(app)}")
    print(f"  Server name: {app.name}")

    # Check handlers exist
    handlers_to_check = [
        'list_tools',
        'call_tool',
        'handle_set_address',
        'handle_check_schedule',
        'handle_get_next_outage',
        'handle_get_outages_for_day',
        'format_schedule_response'
    ]

    # Import server module to check functions
    import server as server_module

    all_present = True
    print("\nChecking handler functions:")
    for handler in handlers_to_check:
        if hasattr(server_module, handler):
            func = getattr(server_module, handler)
            if inspect.isfunction(func) or inspect.iscoroutinefunction(func):
                print(f"  ✓ {handler}")
            else:
                print(f"  ~ {handler} (not a function)")
        else:
            print(f"  ✗ {handler} - MISSING")
            all_present = False

    return all_present


def test_config():
    """Test that config is working."""
    print("\n" + "=" * 60)
    print("Testing Config Module")
    print("=" * 60)

    try:
        from config import config, Address, OutageSchedule, ScheduleCache
        print("\n✓ Config imports successful")
        print(f"  Config directory: {config.config_dir}")
        print(f"  Config file: {config.config_file}")
        print(f"  Cache file: {config.cache_file}")

        # Test address model
        test_addr = Address(
            city="м. Дніпро",
            street="Просп. Миру",
            house_number="4"
        )
        print(f"\n✓ Address model works: {test_addr.to_string()}")

        return True
    except Exception as e:
        print(f"\n✗ Config error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_parser_import():
    """Test that parser module imports correctly."""
    print("\n" + "=" * 60)
    print("Testing Parser Module")
    print("=" * 60)

    try:
        from parser import DTEKParser, fetch_dtek_schedule
        print("\n✓ Parser imports successful")
        print(f"  DTEKParser class: {DTEKParser}")
        print(f"  fetch_dtek_schedule function: {fetch_dtek_schedule}")
        return True
    except Exception as e:
        print(f"\n✗ Parser error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP SERVER VALIDATION SUITE")
    print("=" * 60 + "\n")

    results = []

    # Test 1: Imports
    imports_ok, app = test_imports()
    results.append(("Imports", imports_ok))

    # Test 2: Server structure (only if imports worked)
    if imports_ok and app:
        results.append(("Server Structure", test_server_structure(app)))
    else:
        results.append(("Server Structure", False))

    # Test 3: Config
    results.append(("Config Module", test_config()))

    # Test 4: Parser
    results.append(("Parser Module", test_parser_import()))

    # Summary
    print("\n\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status:12} {test_name}")

    print("\n" + "=" * 60)
    all_passed = all(passed for _, passed in results)
    if all_passed:
        print("✓ ALL VALIDATIONS PASSED")
        print("\nThe MCP server is properly configured and ready to use.")
        print("Start it with: python -m src.server")
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("\nPlease fix the issues above before using the server.")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
