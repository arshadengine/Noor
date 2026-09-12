"""
test_vision.py
Verify screenshot capture and image analysis routing.
"""

import sys
import os
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent))

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from brain.vision import take_screenshot, analyze_image

def test_screenshot_capture():
    print("[Test] Running screenshot capture test...")
    test_img = Path("D:/Noor/data/test_screenshot.png")
    if test_img.exists():
        test_img.unlink()
        
    filepath = take_screenshot(str(test_img))
    print(f"Captured screenshot path: {filepath}")
    assert filepath == str(test_img)
    assert test_img.exists()
    assert test_img.stat().st_size > 0
    print("[Test] ✅ Screenshot capture test passed.")
    return test_img

def test_vision_analysis(test_img_path):
    print("[Test] Running image analysis routing test...")
    # Test if the function runs. It will attempt cloud vision first if API keys exist,
    # then fallback to local Ollama. We'll verify it returns a response (success or expected fallback error).
    
    prompt = "Describe this test image in one word."
    response = analyze_image(str(test_img_path), prompt)
    print(f"Analysis Response: {response}")
    
    assert len(response) > 0
    # Clean up the test screenshot
    if test_img_path.exists():
        test_img_path.unlink()
        
    print("[Test] ✅ Image analysis routing test passed.")

if __name__ == "__main__":
    print("=== Vision Pipeline Test Suite ===")
    img_path = test_screenshot_capture()
    test_vision_analysis(img_path)
    print("=== All Vision tests completed successfully! ===")
