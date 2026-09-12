"""
test_os_control.py
Verify command safety validations and application opening controls.
"""

import sys
import os
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent))

from brain.os_agent import is_safe_command, execute_safe_command, open_app

def test_safety_checks():
    print("[Test] Running safety checks...")
    
    # Safe commands
    assert is_safe_command("dir") == True
    assert is_safe_command("ls -la") == True
    assert is_safe_command("echo Hello World") == True
    assert is_safe_command("git status") == True
    
    # Unsafe commands (contains blocked keywords)
    assert is_safe_command("del file.txt") == False
    assert is_safe_command("rm -rf /") == False
    assert is_safe_command("shutdown /s") == False
    assert is_safe_command("taskkill /F /IM notepad.exe") == False
    
    # Unsafe command (contains redirection operators)
    assert is_safe_command("echo hello > out.txt") == False
    assert is_safe_command("dir | findstr txt") == False
    
    print("[Test] ✅ Safety checks passed.")

def test_command_execution():
    print("[Test] Running command execution checks...")
    
    # Execute a safe command
    output = execute_safe_command("echo Noor OSAgent Test")
    print(f"Command output: {output.strip()}")
    assert "Noor OSAgent Test" in output
    
    # Execute an unsafe command (should be rejected)
    output_unsafe = execute_safe_command("del test_file.txt")
    print(f"Unsafe command response: {output_unsafe.strip()}")
    assert "rejected" in output_unsafe or "unsafe" in output_unsafe
    
    print("[Test] ✅ Command execution checks passed.")

def test_app_opening():
    print("[Test] Running app opening checks...")
    
    # Try opening notepad (whitelisted)
    # On headless/testing setups, this will spawn notepad.exe, which is fine
    res = open_app("notepad")
    print(f"Open app response: {res}")
    assert "Successfully launched" in res
    
    # Try opening an unwhitelisted app
    res_unsafe = open_app("malicious_tool")
    print(f"Open unsafe app response: {res_unsafe}")
    assert "not in the safe whitelist" in res_unsafe
    
    print("[Test] ✅ App opening checks passed.")

if __name__ == "__main__":
    print("=== OS Control Agent Test Suite ===")
    test_safety_checks()
    test_command_execution()
    test_app_opening()
    print("=== All OS Control tests completed successfully! ===")
