"""
brain/llm.py
─────────────────────────────────────────────────────
Noor's Orchestrated LLM & Subsystem Wrapper.

Routes user requests through Stage 1 Intent Classification and Stage 2 Model Router,
manages conversation context, injects memory/preferences, enforces
anti-hallucination verification, and provides backward-compatibility exports.
"""

from __future__ import annotations

import os
import json
import httpx
import requests
from pathlib import Path
from typing import Generator, Iterator, Any

from dotenv import load_dotenv

from brain.personality import detect_mode, build_system_prompt, get_mode_emoji
from brain.memory import (
    init_db, save_message, get_recent_messages, retrieve_context,
    save_memory, extract_facts_from_message
)
from brain.search import needs_search, web_search
from brain.intent import classify_intent
from brain.router import route_and_execute_stream, route_and_execute_generate

try:
    from brain.embeddings import embed
    EMBEDDINGS_AVAILABLE = True
except Exception:
    EMBEDDINGS_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

load_dotenv(Path(__file__).parent.parent / ".env")

FAST_MODEL = os.getenv("NOOR_FAST_MODEL", "qwen2.5-coder:latest")
HEAVY_MODEL = os.getenv("NOOR_HEAVY_MODEL", "gemma4:latest")
CODER_MODEL = os.getenv("NOOR_CODER_MODEL", "qwen2.5-coder:latest")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
CONV_WINDOW = int(os.getenv("CONVERSATION_WINDOW", "20"))


# Backward-compatibility API exports for subagents & modules
def get_gemini_client():
    """Backward-compatible client getter for subagents/modules."""
    from brain.providers.gemini import GeminiProvider
    p = GeminiProvider()
    try:
        return p._get_client()
    except Exception:
        return None


def call_groq_stream(messages: list[dict[str, Any]], model: str = "", system_instruction: str = "") -> Generator[str, None, None]:
    """Backward-compatible streaming wrapper for Groq."""
    from brain.providers.groq import GroqProvider
    p = GroqProvider()
    yield from p.stream(messages, model=model or None, system_prompt=system_instruction)


def call_openrouter_stream(messages: list[dict[str, Any]], model: str = "", system_instruction: str = "") -> Generator[str, None, None]:
    """Backward-compatible streaming wrapper for OpenRouter."""
    from brain.providers.openrouter import OpenRouterProvider
    p = OpenRouterProvider()
    yield from p.stream(messages, model=model or None, system_prompt=system_instruction)


def call_groq_non_stream(messages: list[dict[str, Any]], model: str = "", system_instruction: str = "") -> str:
    """Backward-compatible non-streaming wrapper for Groq."""
    from brain.providers.groq import GroqProvider
    p = GroqProvider()
    return p.generate(messages, model=model or None, system_prompt=system_instruction)


def call_openrouter_non_stream(messages: list[dict[str, Any]], model: str = "", system_instruction: str = "") -> str:
    """Backward-compatible non-streaming wrapper for OpenRouter."""
    from brain.providers.openrouter import OpenRouterProvider
    p = OpenRouterProvider()
    return p.generate(messages, model=model or None, system_prompt=system_instruction)


def check_ollama() -> dict:
    """Check if Ollama is running and return available models."""
    from brain.health import health_monitor
    res = health_monitor.providers.get("ollama", {})
    return {"status": "ok" if res.get("status") == "ONLINE" else "degraded", "details": res}


def chat(
    message: str,
    session_id: str,
    stream: bool = True,
    _bypass_verification: bool = False,
) -> Generator[tuple[str, str], None, None]:
    """
    Main chat entrypoint. 
    1. Check Anti-Hallucination verification for factual/historical queries
    2. Stage 1 Intent Classification -> Direct OS Agent / Vision Agent if applicable
    3. Stage 2 Intelligent Model Routing & Orchestrated execution
    4. Memory saving + Fact extraction
    """
    import time
    
    # Step 0: Check if we need to enforce evidence-based self-check (Anti-Hallucination)
    if not _bypass_verification:
        msg_lower = message.lower()
        historical_keywords = [
            "what did i", "what file", "what project", "yesterday", "work on",
            "working on", "modify", "edit", "delete", "created", "open",
            "last", "date", "history", "records", "modified"
        ]
        is_historical = any(k in msg_lower for k in historical_keywords) or any(char.isdigit() for char in message)
        
        if is_historical:
            print("[Self-Check] Factual/Historical query detected. Running verification layer...")
            
            context_memories: list[str] = []
            query_embedding: list[float] | None = None
            if EMBEDDINGS_AVAILABLE:
                try:
                    query_embedding = embed(message)
                    context_memories = retrieve_context(query_embedding)
                except Exception:
                    pass
            
            from brain.memory import get_preference
            active_project = get_preference("active_project")
            if active_project:
                project_context = get_preference("active_project_context")
                if project_context:
                    context_memories.append(project_context)
            
            raw_response = ""
            final_mode = "friend"
            for token, mode in chat(message, session_id, stream=False, _bypass_verification=True):
                raw_response += token
                final_mode = mode
                
            verified_response, confidence = verify_and_check_hallucination(message, raw_response, context_memories)
            print(f"[Self-Check] Verification complete. Confidence: {confidence}")
            
            if stream:
                words = verified_response.split(" ")
                for i, w in enumerate(words):
                    space = " " if i < len(words) - 1 else ""
                    yield w + space, final_mode
                    time.sleep(0.02)
            else:
                yield verified_response, final_mode
            return

    # Stage 1: Intent Classification & Subsystem Routing
    task_category, required_constraints = classify_intent(message)
    mode = task_category.lower()
    
    query_embedding: list[float] | None = None
    if EMBEDDINGS_AVAILABLE:
        try:
            query_embedding = embed(message)
        except Exception as e:
            print(f"[Noor] Embedding unavailable: {e}")

    save_message(session_id, "user", message, mode, embedding=query_embedding)
    history = get_recent_messages(session_id, limit=CONV_WINDOW)

    # Subsystem Direct Dispatch: OS Agent
    if task_category == "OS_CONTROL":
        from brain.agents import OSAgent
        full_resp = ""
        for chunk in OSAgent.run_stream(message, history=history):
            full_resp += chunk
            yield chunk, "os"
        _save_response_and_extract_facts(message, full_resp, session_id, "os")
        return
        
    # Subsystem Direct Dispatch: Vision Agent
    if task_category == "VISION":
        from brain.agents import VisionAgent
        import re
        image_path = None
        match = re.search(r"🖼️ \[Attached Image\]: ([^\n]+)", message)
        if match:
            image_path = match.group(1).strip()
            message_clean = message.replace(f"🖼️ [Attached Image]: {image_path}", "").strip()
            if not message_clean:
                message_clean = "Describe this image."
        else:
            message_clean = message
            
        response_text = VisionAgent.run(message_clean, image_path=image_path)
        yield response_text, "vision"
        _save_response_and_extract_facts(message, response_text, session_id, "vision")
        return

    # Stage 2: LLM Router Pipeline
    context_memories: list[str] = []
    if EMBEDDINGS_AVAILABLE and query_embedding is not None:
        try:
            context_memories = retrieve_context(query_embedding)
        except Exception as e:
            print(f"[Noor] Context retrieval failed: {e}")

    system_prompt = build_system_prompt(mode=mode, memories=context_memories)

    # Inject Learning Engine Corrections
    from brain.memory import find_matching_corrections, get_graph_summary
    corrections = find_matching_corrections(message)
    if corrections:
        corrections_block = "\n\n--- CRITICAL USER PREFERENCES & CORRECTED RULES (Adhere strictly) ---\n" + "\n".join(f"- {c}" for c in corrections)
        system_prompt += corrections_block

    # Inject Knowledge Graph Summary
    graph_summary = get_graph_summary()
    if graph_summary and not graph_summary.startswith("Knowledge Graph is empty"):
        graph_block = "\n\n--- RELATIONSHIP KNOWLEDGE GRAPH ---\n" + graph_summary
        system_prompt += graph_block

    # Inject Active Project Context
    from brain.memory import get_preference
    active_project = get_preference("active_project")
    if active_project:
        project_context = get_preference("active_project_context")
        if project_context:
            system_prompt += f"\n\n--- ACTIVE PROJECT CONTEXT ({active_project}) ---\n{project_context}\n"

    # Inject Research Grounding if needed
    from brain.agents import PlannerAgent, ResearchAgent
    route_decision = PlannerAgent.route(message)
    if route_decision.get("needs_search"):
        try:
            research_brief = ResearchAgent.gather_research(message)
            if research_brief:
                system_prompt += "\n\n--- RESEARCH BRIEF (LIVE WEB RESULTS) ---\n" + research_brief
        except Exception as e:
            print(f"[Noor] Research Agent failed: {e}")

    messages_payload = []
    for msg in history:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})

    full_response = ""
    if stream:
        for token, cat, model_used in route_and_execute_stream(
            messages=messages_payload,
            system_prompt=system_prompt,
            forced_task_category=task_category
        ):
            full_response += token
            yield token, mode
    else:
        full_response, cat, model_used = route_and_execute_generate(
            messages=messages_payload,
            system_prompt=system_prompt,
            forced_task_category=task_category
        )
        yield full_response, mode

    _save_response_and_extract_facts(message, full_response, session_id, mode)


def simple_query(prompt: str, system: str = "") -> str:
    """Non-streaming query routed through Stage 2 LLM Router."""
    messages = [{"role": "user", "content": prompt}]
    response_text, cat, model_used = route_and_execute_generate(
        messages=messages,
        system_prompt=system
    )
    return response_text


def _save_response_and_extract_facts(message: str, full_response: str, session_id: str, mode: str) -> None:
    """Helper to save response to memory and extract new facts."""
    resp_embedding: list[float] | None = None
    if EMBEDDINGS_AVAILABLE and full_response:
        try:
            resp_embedding = embed(full_response)
        except Exception:
            pass

    save_message(session_id, "assistant", full_response, mode, embedding=resp_embedding)

    if mode in ["os", "vision"]:
        return

    facts = extract_facts_from_message(message)
    for fact_text, importance, tags in facts:
        fact_embedding = None
        if EMBEDDINGS_AVAILABLE:
            try:
                fact_embedding = embed(fact_text)
            except Exception:
                pass
        save_memory(fact_text, importance=importance, tags=tags, embedding=fact_embedding)

    if full_response and not full_response.startswith("⚠️ [Noor Error]"):
        try:
            import threading
            from brain.agents import MemoryAgent
            t = threading.Thread(
                target=MemoryAgent.process_conversation_turn,
                args=(message, full_response),
                name="NoorMemoryAgent"
            )
            t.start()
        except Exception as e:
            print(f"[Noor MemoryAgent] Thread trigger failed: {e}")


def verify_and_check_hallucination(message: str, response: str, context: list[str]) -> tuple[str, float]:
    """Perform agent self-check on the response."""
    msg_lower = message.lower()
    resp_lower = response.lower()
    
    context_str = "\n".join(context).lower()
    clean_context = context_str
    for header in ["active project context", "relation knowledge graph", "critical user preferences"]:
        if header in clean_context:
            parts = clean_context.split(header)
            clean_context = "".join(parts[1:])
            
    has_evidence = len(clean_context.strip()) > 20
    
    import re
    dates_in_msg = re.findall(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\s+\d{4}\b', msg_lower)
    if not dates_in_msg:
        dates_in_msg = re.findall(r'\b\d{4}-\d{2}-\d{2}\b', msg_lower)
        
    if dates_in_msg:
        date_matched = False
        for d in dates_in_msg:
            if d.lower() in context_str:
                date_matched = True
                break
        if not date_matched:
            has_evidence = False
            
    if not has_evidence:
        return "I couldn't find any local records or activity history in my database to answer that.", 0.0
        
    files_in_resp = re.findall(r'\b([\w\-]+\.(?:txt|py|json|md|html|css|js|ts|jsx|tsx|pdf|docx|xlsx|zip|png|jpg|jpeg))\b', resp_lower)
    for f in files_in_resp:
        if f in ["memory.py", "llm.py", "agents.py", "main.py", "requirements.txt", ".env"]:
            continue
        if f not in context_str:
            return f"I couldn't find verified records of the file '{f}' in my database or workspace context.", 0.3
            
    confidence = 1.0
    uncertainty_phrases = ["i think", "maybe", "probably", "perhaps", "i guess", "i'm not sure", "difficult to say", "could be", "unknown"]
    for p in uncertainty_phrases:
        if p in resp_lower:
            confidence -= 0.25
            
    if confidence < 0.5:
        return "I found multiple project folders or uncertain references. Could you please specify which project or folder you are referring to?", confidence
        
    return response, confidence
