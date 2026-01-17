"""
MT5 Installation Verification Script

This script verifies that the MetaTrader5 library is properly installed
and can communicate with the MT5 terminal.

Requirements:
- MetaTrader5 terminal must be installed and running
- Algo Trading must be enabled in MT5
- Valid MT5 account credentials

Usage:
    python tests/test_mt5_installation.py
"""

import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_mt5_import():
    """Test 1: Verify MetaTrader5 module can be imported"""
    try:
        import MetaTrader5 as mt5
        print(f"✓ MetaTrader5 module imported successfully (version {mt5.__version__})")
        return True
    except ImportError as e:
        print(f"✗ Failed to import MetaTrader5: {e}")
        return False


def test_mt5_initialize():
    """Test 2: Verify MT5.initialize() works (requires MT5 terminal running)"""
    try:
        import MetaTrader5 as mt5

        # Attempt to initialize MT5
        if not mt5.initialize():
            error_code = mt5.last_error()
            print(f"✗ MT5.initialize() failed: {error_code}")
            print("  Make sure MT5 terminal is installed and running")
            return False

        print("✓ MT5.initialize() succeeded")

        # Get terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            print("✗ Failed to get terminal info")
            mt5.shutdown()
            return False

        print(f"  Terminal: {terminal_info.name}")
        print(f"  Path: {terminal_info.path}")
        print(f"  Company: {terminal_info.company}")
        print(f"  Build: {terminal_info.build}")

        # Shutdown MT5
        mt5.shutdown()
        return True

    except Exception as e:
        print(f"✗ MT5.initialize() error: {e}")
        return False


def test_mt5_terminal_paths():
    """Test 3: Check common MT5 installation paths"""
    import os

    common_paths = [
        "C:/Program Files/MetaTrader 5/terminal64.exe",
        "C:/Program Files (x86)/MetaTrader 5/terminal64.exe",
        "C:/Program Files/MetaTrader 5/terminal.exe",
        "C:/Program Files (x86)/MetaTrader 5/terminal.exe",
        "C:/Program Files/MetaTrader 5 Terminal/terminal64.exe",
        "C:/Program Files/MetaTrader 5 Terminal/terminal.exe",
    ]

    found = False
    for path in common_paths:
        if os.path.exists(path):
            print(f"✓ Found MT5 terminal at: {path}")
            found = True

    if not found:
        print("✗ MT5 terminal not found in common installation paths:")
        for path in common_paths:
            print(f"    - {path}")
        print("  Download MT5 from: https://www.metatrader5.com/en/download")
        return False

    return True


def main():
    """Run all MT5 installation tests"""
    print("=" * 60)
    print("MT5 Installation Verification")
    print("=" * 60)
    print()

    tests = [
        ("MetaTrader5 Import", test_mt5_import),
        ("MT5 Terminal Path Check", test_mt5_terminal_paths),
        ("MT5 Initialize", test_mt5_initialize),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n[Test] {test_name}")
        print("-" * 40)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            results.append((test_name, False))
        print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)

    return all(r for _, r in results)


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
