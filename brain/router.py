"""
brain/router.py
─────────────────────────────────────────────────────
Stage 2: LLM Router & Orchestration Engine for Noor.

Coordinates candidate scoring, constraint enforcement, decision caching,
provider execution, health latency monitoring, telemetry logging, and
automatic failover handling across model providers.
"""

from __future__ import annotations
import time
from typing import Generator, Any

from brain.intent import classify_intent
from brain.registry import MODELS
from brain.scoring import rank_candidate_models
from brain.health import health_monitor
from brain.cache import routing_cache
from brain.telemetry import log_telemetry_event
from brain.providers import GeminiProvider, GroqProvider, OpenRouterProvider, OllamaProvider, BaseProvider

# Cached Provider Instances
_provider_instances: dict[str, BaseProvider] = {}


def get_provider_instance(provider_name: str) -> BaseProvider:
    """Lazy initialize and return provider instance."""
    if provider_name not in _provider_instances:
        if provider_name == "gemini":
            _provider_instances[provider_name] = GeminiProvider()
        elif provider_name == "groq":
            _provider_instances[provider_name] = GroqProvider()
        elif provider_name == "openrouter":
            _provider_instances[provider_name] = OpenRouterProvider()
        elif provider_name == "ollama":
            _provider_instances[provider_name] = OllamaProvider()
        else:
            raise ValueError(f"Unknown provider: '{provider_name}'")
    return _provider_instances[provider_name]


def route_and_execute_stream(
    messages: list[dict[str, Any]],
    system_prompt: str = "",
    user_preference: str = "speed",
    forced_task_category: str | None = None
) -> Generator[tuple[str, str, str], None, None]:
    """
    Main streaming orchestration pipeline.
    Yields: (token, task_category, selected_model_name)
    Handles ranking, candidate selection, execution, and automatic failover.
    """
    last_user_msg = messages[-1]["content"] if messages else ""
    
    # 1. Intent Classification
    if forced_task_category:
        task_category = forced_task_category
        required_constraints = {}
    else:
        task_category, required_constraints = classify_intent(last_user_msg)

    # 2. Score & Rank Candidate Models
    candidate_models = rank_candidate_models(task_category, required_constraints, user_preference)

    # 3. Check Decision Cache
    cached_model = routing_cache.get(task_category, user_preference, required_constraints)
    if cached_model and cached_model in MODELS:
        print(f"[Noor Router] Using cached decision for task '{task_category}': {cached_model}")
        remaining = [c for c in candidate_models if c[0] != cached_model]
        candidate_models = [(cached_model, 9.9)] + remaining

    # Ensure local Ollama candidates exist as ultimate fallbacks
    existing_keys = {c[0] for c in candidate_models}
    for local_key in ("ollama_qwen", "ollama_gemma", "ollama_llama"):
        if local_key not in existing_keys:
            candidate_models.append((local_key, 4.0))

    failover_chain: list[str] = []
    
    # 4. Iterate Candidates with Automatic Failover
    for candidate_key, score in candidate_models:
        spec = MODELS[candidate_key]
        provider_name = spec["provider"]
        model_name = spec["model_name"]
        
        print(f"[Noor Router] Attempting execution via '{candidate_key}' ({provider_name} :: {model_name}) [Score: {score}]...")
        start_time = time.time()
        
        try:
            provider = get_provider_instance(provider_name)
            stream_gen = provider.stream(messages=messages, model=model_name, system_prompt=system_prompt)
            
            first_token_received = False
            token_count = 0
            
            for token in stream_gen:
                if not first_token_received:
                    first_token_received = True
                    first_token_latency = (time.time() - start_time) * 1000.0
                    health_monitor.record_success(provider_name, first_token_latency)
                
                token_count += 1
                yield token, task_category, candidate_key

            # Successfully completed full stream
            total_latency = (time.time() - start_time) * 1000.0
            routing_cache.set(task_category, candidate_key, user_preference, required_constraints)
            log_telemetry_event(
                task_category=task_category,
                selected_model=candidate_key,
                provider=provider_name,
                score=score,
                latency_ms=total_latency,
                success=True,
                failover_chain=failover_chain
            )
            return

        except Exception as e:
            err_msg = str(e)
            print(f"[Noor Router] Failover Triggered! Candidate '{candidate_key}' failed: {err_msg}")
            failover_chain.append(candidate_key)
            health_monitor.record_failure(provider_name, err_msg)
            log_telemetry_event(
                task_category=task_category,
                selected_model=candidate_key,
                provider=provider_name,
                score=score,
                latency_ms=(time.time() - start_time) * 1000.0,
                success=False,
                failover_chain=failover_chain,
                error_msg=err_msg
            )
            # Loop continues to next candidate in ranking!

    # If all candidates fail completely
    fallback_err = "⚠️ [Noor Error] All available cloud and local LLM providers failed to respond."
    yield fallback_err, task_category, "none"


def route_and_execute_generate(
    messages: list[dict[str, Any]],
    system_prompt: str = "",
    user_preference: str = "speed",
    forced_task_category: str | None = None
) -> tuple[str, str, str]:
    """
    Non-streaming orchestration pipeline.
    Returns: (full_text, task_category, selected_model_name)
    """
    last_user_msg = messages[-1]["content"] if messages else ""
    
    if forced_task_category:
        task_category = forced_task_category
        required_constraints = {}
    else:
        task_category, required_constraints = classify_intent(last_user_msg)

    candidate_models = rank_candidate_models(task_category, required_constraints, user_preference)

    cached_model = routing_cache.get(task_category, user_preference, required_constraints)
    if cached_model and cached_model in MODELS:
        remaining = [c for c in candidate_models if c[0] != cached_model]
        candidate_models = [(cached_model, 9.9)] + remaining

    existing_keys = {c[0] for c in candidate_models}
    for local_key in ("ollama_qwen", "ollama_gemma", "ollama_llama"):
        if local_key not in existing_keys:
            candidate_models.append((local_key, 4.0))

    failover_chain: list[str] = []

    for candidate_key, score in candidate_models:
        spec = MODELS[candidate_key]
        provider_name = spec["provider"]
        model_name = spec["model_name"]
        
        start_time = time.time()
        try:
            provider = get_provider_instance(provider_name)
            response_text = provider.generate(messages=messages, model=model_name, system_prompt=system_prompt)
            latency_ms = (time.time() - start_time) * 1000.0
            
            health_monitor.record_success(provider_name, latency_ms)
            routing_cache.set(task_category, candidate_key, user_preference, required_constraints)
            log_telemetry_event(
                task_category=task_category,
                selected_model=candidate_key,
                provider=provider_name,
                score=score,
                latency_ms=latency_ms,
                success=True,
                failover_chain=failover_chain
            )
            return response_text, task_category, candidate_key

        except Exception as e:
            err_msg = str(e)
            print(f"[Noor Router] Generate failover: '{candidate_key}' failed: {err_msg}")
            failover_chain.append(candidate_key)
            health_monitor.record_failure(provider_name, err_msg)
            log_telemetry_event(
                task_category=task_category,
                selected_model=candidate_key,
                provider=provider_name,
                score=score,
                latency_ms=(time.time() - start_time) * 1000.0,
                success=False,
                failover_chain=failover_chain,
                error_msg=err_msg
            )

    return "⚠️ [Noor Error] All available cloud and local LLM providers failed.", task_category, "none"
