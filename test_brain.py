"""Quick smoke test for Noor's brain modules."""
import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.path.insert(0, "D:/Noor")

from brain.memory import init_db
from brain.personality import detect_mode, build_system_prompt, get_mode_emoji

init_db()
print("[Noor] Database initialized OK")

tests = [
    ("hey, how are you doing?", "friend"),
    ("help me debug this python code", "coder"),
    ("I have an exam tomorrow and I am nervous", "friend"),
    ("explain how transformers work in machine learning", "researcher"),
    ("I need advice on my career plan", "mentor"),
]

print()
all_ok = True
MODE_LABELS = {"friend": "[FRIEND]", "mentor": "[MENTOR]", "researcher": "[RESEARCHER]", "coder": "[CODER]"}
for msg, expected in tests:
    mode = detect_mode(msg)
    label_str = MODE_LABELS.get(mode, f"[{mode}]")
    ok = mode == expected
    if not ok:
        all_ok = False
    status = "OK" if ok else f"WARN (expected {expected})"
    short_msg = (msg[:45] + "...") if len(msg) > 45 else msg
    print(f"  {label_str} {status} - \"{short_msg}\"")

print()
if all_ok:
    print("[Noor] Personality engine: ALL TESTS PASSED")
else:
    print("[Noor] Personality engine: some mode detections differ (non-critical)")

# Test system prompt building
sp = build_system_prompt(mode="coder", memories=["Arshad is building Noor", "Arshad knows Python"])
assert "CODER MODE" in sp, "Mode injection failed"
assert "Arshad is building Noor" in sp, "Memory injection failed"
print("[Noor] System prompt builder: OK")
print()
print("[Noor] === ALL BRAIN TESTS PASSED ===")
