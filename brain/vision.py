"""
brain/vision.py
─────────────────────────────────────────────────────
Noor's Vision Pipeline.

Handles screen capture (screenshots) and image/screenshot analysis
using local Ollama vision models or active cloud APIs (Gemini/OpenRouter).
"""

from __future__ import annotations

import os
import sys
import base64
from pathlib import Path
from PIL import Image, ImageGrab
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

from brain.memory import log_agent_action
from brain.llm import get_gemini_client

def take_screenshot(output_path: str = None) -> str:
    """Capture a screenshot of the desktop and save it to disk."""
    if not output_path:
        temp_dir = Path("D:/Noor/data")
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(temp_dir / "temp_screenshot.png")
        
    log_agent_action("Vision", f"Capturing screenshot: {output_path}")
    try:
        # Grab screen and save
        img = ImageGrab.grab()
        img.save(output_path, "PNG")
        log_agent_action("Vision", "Screenshot captured successfully.")
        return output_path
    except Exception as e:
        err = f"❌ Failed to capture screenshot: {e}"
        log_agent_action("Vision", err)
        return err


def analyze_image(image_path: str, prompt: str = "Describe this image in detail.") -> str:
    """Analyze an image or screenshot using the active model (Gemini, OpenRouter, or Ollama)."""
    log_agent_action("Vision", f"Analyzing image '{image_path}' with prompt: '{prompt}'")
    
    if not os.path.exists(image_path):
        err = f"⚠️ [Vision Error] Image file not found: {image_path}"
        log_agent_action("Vision", err)
        return err

    # 1. Direct Gemini Cloud Model (Multi-modal)
    gemini_client = get_gemini_client()
    if gemini_client:
        gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        log_agent_action("Vision", f"Routing analysis to Gemini Cloud Model: {gemini_model_name}")
        try:
            img = Image.open(image_path)
            # Use generate_content with image object
            res = gemini_client.models.generate_content(
                model=gemini_model_name,
                contents=[img, prompt]
            )
            ans = res.text or ""
            log_agent_action("Vision", "Gemini analysis completed.")
            return ans
        except Exception as e:
            print(f"[Noor Vision] Gemini analysis failed: {e}. Falling back...")

    # 2. OpenRouter Cloud Model (Multi-modal)
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
    if openrouter_api_key:
        openrouter_model_name = os.getenv("OPENROUTER_VISION_MODEL", "")
        if not openrouter_model_name:
            env_model = os.getenv("OPENROUTER_MODEL", "")
            if env_model and "gemma-4" not in env_model and "coder" not in env_model:
                openrouter_model_name = env_model
            else:
                openrouter_model_name = "google/gemini-2.0-flash"  # Default vision model
                
        log_agent_action("Vision", f"Routing analysis to OpenRouter Model: {openrouter_model_name}")
        try:
            # Base64 encode image
            with open(image_path, "rb") as f:
                img_data = f.read()
            mime_type = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
            b64_str = base64.b64encode(img_data).decode("utf-8")
            image_url = f"data:{mime_type};base64,{b64_str}"
            
            # Formulate OpenRouter multi-modal payload
            payload = {
                "model": openrouter_model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ]
            }
            
            import requests
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openrouter_api_key}",
                "Content-Type": "application/json",
            }
            res = requests.post(url, headers=headers, json=payload, timeout=25.0)
            if res.status_code == 200:
                ans = res.json()["choices"][0]["message"]["content"]
                log_agent_action("Vision", "OpenRouter analysis completed.")
                return ans
            else:
                print(f"[Noor Vision] OpenRouter vision failed: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"[Noor Vision] OpenRouter vision failed: {e}")
 
    # 3. Local Ollama Vision Model (Llava / Moondream / Qwen2-VL)
    log_agent_action("Vision", "Falling back to local Ollama Vision Model...")
    try:
        import ollama
        # Determine vision model
        models = [m.model for m in ollama.list().models]
        vision_model = None
        for m in ["llava:latest", "llava", "qwen2-vl", "qwen2-vl:latest", "qwen2-vl:2b", "qwen2-vl:7b", "moondream", "moondream:latest", "minicpm-v", "minicpm-v:latest"]:
            if m in models:
                vision_model = m
                break
                
        # If no vision model exists, default to 'llava' and hope it works (or prompt to pull)
        if not vision_model:
            vision_model = "llava"
            log_agent_action("Vision", "No active vision model found in Ollama. Will attempt to run 'llava'.")
            
        res = ollama.chat(
            model=vision_model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path]
                }
            ]
        )
        ans = res["message"]["content"]
        log_agent_action("Vision", f"Local Ollama analysis ({vision_model}) completed.")
        return ans
    except Exception as e:
        err = f"❌ Local vision analysis failed: {e}. Make sure an Ollama vision model (e.g. 'llava' or 'moondream') is installed."
        log_agent_action("Vision", err)
        return err
