#!/usr/bin/env python3
"""
TraceTap Module Tests

Simple tests to verify that all modules are working correctly.
Run this before using TraceTap to ensure everything is set up properly.
"""

import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    print("🧪 Testing module imports...")
    
    try:
        from filters import RequestFilter
        print("   ✓ filters.py")
    except ImportError as e:
        print(f"   ✗ filters.py - {e}")
        return False
    
    try:
        from exporters import PostmanExporter, RawLogExporter
        print("   ✓ exporters.py")
    except ImportError as e:
        print(f"   ✗ exporters.py - {e}")
        return False
    
    try:
        from utils import safe_body, calc_duration, status_color
        print("   ✓ utils.py")
    except ImportError as e:
        print(f"   ✗ utils.py - {e}")
        return False
    
    try:
        import tracetap_addon
        print("   ✓ tracetap_addon.py")
    except ImportError as e:
        print(f"   ✗ tracetap_addon.py - {e}")
        return False
    
    return True


def test_filter_logic():
    """Test the filtering logic."""
    print("\n🧪 Testing filter logic...")
    
    from filters import RequestFilter
    
    # Test 1: No filters (capture all)
    filter_all = RequestFilter([], None)
    assert filter_all.should_capture("api.example.com", "https://api.example.com/test")
    print("   ✓ No filters - captures all")
    
    # Test 2: Exact match
    filter_exact = RequestFilter(["api.example.com"], None)
    assert filter_exact.should_capture("api.example.com", "https://api.example.com/test")
    assert not filter_exact.should_capture("other.com", "https://other.com/test")
    print("   ✓ Exact host matching")
    
    # Test 3: Wildcard match
    filter_wildcard = RequestFilter(["*.example.com"], None)
    assert filter_wildcard.should_capture("api.example.com", "https://api.example.com/test")
    assert filter_wildcard.should_capture("auth.example.com", "https://auth.example.com/test")
    assert not filter_wildcard.should_capture("other.com", "https://other.com/test")
    print("   ✓ Wildcard matching")
    
    # Test 4: Regex match
    filter_regex = RequestFilter([], r"api\..*\.com")
    assert filter_regex.should_capture("api.example.com", "https://api.example.com/test")
    assert filter_regex.should_capture("api.test.com", "https://api.test.com/test")
    assert not filter_regex.should_capture("www.example.com", "https://www.example.com/test")
    print("   ✓ Regex matching")
    
    return True


def test_utils():
    """Test utility functions."""
    print("\n🧪 Testing utility functions...")
    
    from utils import safe_body, status_color
    
    # Test safe_body
    text_body = safe_body("Hello", b"")
    assert text_body == "Hello"
    print("   ✓ safe_body - text")
    
    binary_body = safe_body("", b"\x00\x01\x02")
    assert "[binary data:" in binary_body
    print("   ✓ safe_body - binary")
    
    # Test status_color
    assert status_color(200) == "\033[32m"  # Green
    assert status_color(404) == "\033[33m"  # Yellow
    assert status_color(500) == "\033[31m"  # Red
    print("   ✓ status_color")
    
    return True


def test_exporters():
    """Test exporter functionality."""
    print("\n🧪 Testing exporters...")
    
    from exporters import PostmanExporter, RawLogExporter
    import tempfile
    import json
    
    # Create sample data
    sample_records = [{
        "time": "2025-10-27T10:00:00",
        "method": "GET",
        "url": "https://api.example.com/test",
        "host": "api.example.com",
        "proto": "HTTP/1.1",
        "req_headers": {"User-Agent": "Test"},
        "req_body": "",
        "status": 200,
        "resp_headers": {"Content-Type": "application/json"},
        "resp_body": '{"result": "ok"}',
        "duration_ms": 100
    }]
    
    # Test Postman export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        PostmanExporter.export(sample_records, "test-session", temp_path)
        with open(temp_path, 'r') as f:
            data = json.load(f)
            assert "info" in data
            assert "item" in data
            assert len(data["item"]) == 1
        print("   ✓ PostmanExporter")
    finally:
        Path(temp_path).unlink(missing_ok=True)
    
    # Test Raw Log export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        RawLogExporter.export(sample_records, "test-session", temp_path, [], "")
        with open(temp_path, 'r') as f:
            data = json.load(f)
            assert "session" in data
            assert "requests" in data
            assert len(data["requests"]) == 1
        print("   ✓ RawLogExporter")
    finally:
        Path(temp_path).unlink(missing_ok=True)
    
    return True


def main():
    """Run all tests."""
    print("╔═══════════════════════════════════════╗")
    print("║   TraceTap Module Tests               ║")
    print("╚═══════════════════════════════════════╝\n")
    
    tests = [
        test_imports,
        test_filter_logic,
        test_utils,
        test_exporters,
    ]
    
    failed = False
    for test in tests:
        try:
            if not test():
                failed = True
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            failed = True
    
    print("\n" + "="*40)
    if failed:
        print("❌ Some tests failed")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        print("\nTraceTap is ready to use!")
        sys.exit(0)


if __name__ == '__main__':
    main()
