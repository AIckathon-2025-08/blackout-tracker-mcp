"""
Test script to verify i18n translations work correctly.
"""
import sys
sys.path.insert(0, 'src')

from i18n import I18n


def test_english_translations():
    """Test English translations (default)."""
    print("=" * 60)
    print("Testing English Translations (Default)")
    print("=" * 60)

    i18n = I18n("en")

    # Test tool descriptions
    check_schedule_desc = i18n.t("tool_descriptions.check_outage_schedule")
    print(f"✓ Tool description: {check_schedule_desc}")
    assert "outage schedule" in check_schedule_desc.lower(), "English translation failed"

    # Test messages
    address_saved = i18n.t("messages.address_saved", address="Test Address")
    print(f"✓ Address saved message: {address_saved}")
    assert "saved" in address_saved.lower() or "address" in address_saved.lower(), "English translation failed"

    # Test schedule labels
    next_outage = i18n.t("schedule.next_outage_title")
    print(f"✓ Next outage title: {next_outage}")
    assert len(next_outage) > 0, "English translation failed"

    print("\n✓ All English translations passed!\n")


def test_ukrainian_translations():
    """Test Ukrainian translations."""
    print("=" * 60)
    print("Testing Ukrainian Translations")
    print("=" * 60)

    i18n = I18n("uk")

    # Test tool descriptions
    check_schedule_desc = i18n.t("tool_descriptions.check_outage_schedule")
    print(f"✓ Tool description: {check_schedule_desc}")
    assert "графік" in check_schedule_desc.lower() or "відключень" in check_schedule_desc.lower(), "Ukrainian translation failed"

    # Test messages
    address_saved = i18n.t("messages.address_saved", address="Тестова Адреса")
    print(f"✓ Address saved message: {address_saved}")
    assert "адрес" in address_saved.lower() or "збережен" in address_saved.lower(), "Ukrainian translation failed"

    # Test schedule labels
    next_outage = i18n.t("schedule.next_outage_title")
    print(f"✓ Next outage title: {next_outage}")
    assert len(next_outage) > 0, "Ukrainian translation failed"

    print("\n✓ All Ukrainian translations passed!\n")


def test_translation_completeness():
    """Test that all required translation keys exist."""
    print("=" * 60)
    print("Testing Translation Completeness")
    print("=" * 60)

    required_keys = [
        "tool_descriptions.check_outage_schedule",
        "tool_descriptions.get_next_outage",
        "tool_descriptions.get_outages_for_day",
        "tool_descriptions.set_address",
        "tool_params.include_possible",
        "tool_params.force_refresh",
        "tool_params.day_of_week",
        "tool_params.schedule_type",
        "messages.address_saved",
        "messages.address_not_configured",
        "messages.error_fetching",
        "messages.no_next_outage",
        "schedule.address_label",
        "schedule.next_outage_title",
        "schedule.type_label",
    ]

    for lang in ["en", "uk"]:
        i18n = I18n(lang)
        print(f"\nChecking {lang.upper()} translations:")

        missing_keys = []
        for key in required_keys:
            try:
                translation = i18n.t(key)
                if not translation or translation == key:
                    missing_keys.append(key)
                else:
                    print(f"  ✓ {key}")
            except Exception as e:
                print(f"  ✗ {key}: {e}")
                missing_keys.append(key)

        if missing_keys:
            print(f"\n✗ Missing translations in {lang}: {missing_keys}")
            sys.exit(1)
        else:
            print(f"  ✓ All required keys present in {lang}")

    print("\n✓ Translation completeness check passed!\n")


if __name__ == "__main__":
    try:
        test_english_translations()
        test_ukrainian_translations()
        test_translation_completeness()

        print("=" * 60)
        print("✓ ALL I18N TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
