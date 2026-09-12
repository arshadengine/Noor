"""
brain/agents.py
─────────────────────────────────────────────────────
Noor's Multi-Agent Architecture.

Defines specialist agents:
  - PlannerAgent: Analyzes intent and routes queries.
  - ResearchAgent: Aggregates web search findings into a brief.
  - CodingAgent: Tailors system prompt for software engineering.
  - MemoryAgent: Dynamically extracts rules/corrections and builds the Knowledge Graph.
"""

from __future__ import annotations

import json
import re
import os
from typing import Generator
from brain.llm import simple_query
from brain.search import web_search
from brain.memory import (
    log_agent_action, save_correction, add_graph_node, add_graph_edge,
    get_graph_summary
)


class PlannerAgent:
    """Agent that plans and routes user queries."""
    
    @staticmethod
    def route(message: str) -> dict:
        """
        Decide the mode and whether search is needed.
        Returns a dict: {"mode": str, "needs_search": bool, "reason": str}
        """
        log_agent_action("Planner", f"Routing message: '{message[:50]}...'")
        
        msg_lower = message.lower().strip()
        
        # 1. Vision Heuristics (Explicit screenshot/image patterns)
        if "🖼️ [attached image]" in msg_lower or "describe my screen" in msg_lower or "describe the screen" in msg_lower or "screenshot and tell me" in msg_lower or "what's on the screen" in msg_lower or "whats on the screen" in msg_lower or "what is on the screen" in msg_lower:
            log_agent_action("Planner", "Route decided (Heuristics): mode=vision, search=False", "Matched vision attachment/request pattern.")
            return {"mode": "vision", "needs_search": False, "reason": "Matched vision attachment/request pattern."}
            
        # 2. OS Control Heuristics (Explicit app open / system info / clipboard / window controls / file operations)
        os_patterns = [
            r"\bopen notepad\b", r"\bopen browser\b", r"\bopen calculator\b", r"\bopen paint\b",
            r"\bopen visual studio code\b", r"\bopen vs code\b", r"\bopen vscode\b", r"\bopen code\b",
            r"\bopen chrome\b", r"\bopen edge\b", r"\bopen terminal\b", r"\bopen task manager\b",
            r"\bopen cmd\b", r"\bopen command prompt\b", r"\bopen powershell\b",
            r"\bdisk space\b", r"\bfree space\b", r"\bdrive space\b", r"\bspace khali\b", r"\bspace free\b",
            r"\bkhali space\b", r"\bkitna space\b", r"\bdisk usage\b",
            r"\bclipboard\b", r"\bclip\b",
            r"\bnotification\b", r"\bnotify\b",
            r"\bclose notepad\b", r"\bclose calculator\b", r"\bclose paint\b", r"\bclose chrome\b", r"\bclose brave\b", r"\bclose app\b",
            r"\bswitch to\b", r"\bswitch window\b", r"\bbring to foreground\b",
            r"\bnotepad\b", r"\bcreate file\b", r"\bwrite file\b", r"\bsave file\b", r"\bcreate karo\b", r"\bsave karo\b", r"\blikh kar save\b",
            r"\braw file\b", r"\bdelete file\b", r"\bedit file\b", r"\bdelete karo\b", r"\bread karo\b", r"\bedit karo\b", r"\bopen folder\b", r"\bopen project\b",
            r"\bopen settings\b", r"\bsettings app\b", r"\bbluetooth\b", r"\bwi-?fi\b", r"\bnetwork settings\b",
            r"\btake screenshot\b", r"\bscreenshot\b", r"\bscreen shot\b", r"\bscreen capture\b",
            r"\bclose settings\b", r"\bclose browser\b", r"\bclose chrome\b", r"\bclose brave\b",
            r"\bairplane mode\b", r"\bairplane\b", r"\bturn on\b", r"\bturn off\b", r"\benable\b", r"\bdisable\b", r"\btoggle\b",
            r"\bhow many files\b", r"\bfiles in\b", r"\blist files\b", r"\blist folder\b", r"\bcontents of\b", r"\bdir\b", r"\bls\b", r"\bshow files\b", r"\b[a-zA-Z]:\\",
            r"\bdelete\b", r"\bremove\b",
            r"\bappend\b", r"\bedit\b",
            r"\bfind\b", r"\bsearch file\b", r"\bwhere is\b", r"\bsummarize\b", r"\bsummary\b",
            r"\bwhat is in\b.*\bfolder\b", r"\bwhat's in\b.*\bfolder\b", r"\bcheck\b.*\bfolder\b", r"\bwhat is inside\b", r"\bwhat's inside\b", r"\bwhats inside\b", r"\bwhats in\b", r"\bwhats inside\b.*\bfolder\b",
            r"^\s*in\s+[\w\-]+\??\s*$",
            r"^\s*inside\s+[\w\-]+\??\s*$",
            r"^\s*in\s+this\??\s*$",
            r"^\s*in\s+it\??\s*$",
            r"\b(?:folder|directory|files?|path)\s+(?:mein|me|kya|hai|hain)\b",
            r"\b(?:mein|me|kya|hai|hain)\s+(?:folder|directory|files?|path)\b",
            r"\b[\w\-]+\s+folder\s+mein\b",
            r"\b[\w\-]+\s+folder\s+me\b",
            r'"[\w\-]+"\s+folder',
            r"'[\w\-]+'\s+folder",
            r"\bactive window\b", r"\bfocused window\b", r"\bcurrent window\b", r"\bfocused app\b", r"\bactive app\b", r"\bcurrent app\b", r"\bfocused application\b", r"\bactive application\b"
        ]
        if any(re.search(pat, msg_lower) for pat in os_patterns):
            log_agent_action("Planner", "Route decided (Heuristics): mode=os, search=False", "Matched explicit application open or OS awareness command.")
            return {"mode": "os", "needs_search": False, "reason": "Matched explicit application open or OS awareness command."}
            
        # 3. Casual Conversation / Greeting Heuristics
        try:
            from brain.personality import _MODE_KEYWORDS
            from brain.search import SEARCH_KEYWORDS
            
            # Check if matches any specialized modes
            has_coder = any(re.search(pat, msg_lower) for pat in _MODE_KEYWORDS.get("coder", []))
            has_researcher = any(re.search(pat, msg_lower) for pat in _MODE_KEYWORDS.get("researcher", []))
            has_mentor = any(re.search(pat, msg_lower) for pat in _MODE_KEYWORDS.get("mentor", []))
            has_search = any(re.search(pat, msg_lower) for pat in SEARCH_KEYWORDS)
            
            greetings = {
                "hi", "hello", "hey", "yo", "sup", "good morning", "good afternoon", "good evening",
                "how are you", "how's it going", "what's up", "howdy", "tell me about yourself",
                "who are you", "what is your name", "what's your name", "tell me about youself"
            }
            is_greeting = any(re.search(r'\b' + re.escape(g) + r'\b', msg_lower) for g in greetings)
            
            # If it's an explicit greeting, route to friend mode
            if is_greeting:
                log_agent_action("Planner", "Route decided (Heuristics): mode=friend, search=False", "Matched greeting.")
                return {"mode": "friend", "needs_search": False, "reason": "Matched greeting."}
        except Exception as he_err:
            print(f"[Noor Planner] Heuristic check failed: {he_err}")
 
        # Fallback to LLM Routing for complex/ambiguous queries
        system_prompt = (
            "You are Noor's Planner Agent. Analyze the user's message and determine:\n"
            "1. The best mode for response. Choices:\n"
            "   - 'friend' (casual conversation)\n"
            "   - 'mentor' (guidance, goals, decisions)\n"
            "   - 'researcher' (fact-checking, concept retrieval, web search)\n"
            "   - 'coder' (programming/debugging)\n"
            "   - 'os' (opening applications, executing safe terminal/shell commands, listing files/folders, counting files, file/directory awareness, asking about files in folders like DBMS, DS, OE, SE, Downloads, Desktop)\n"
            "   - 'vision' (taking screenshots, describing screen content, analyzing uploaded pictures)\n\n"
            "IMPORTANT: If the user refers to folders (like 'DBMS', 'DS', 'OE', 'SE', 'Downloads', 'Desktop', etc.) and asks what is in them, how many files they have, or to perform actions on them (in English, Hindi, Hinglish, e.g. 'DBMS folder mein kya hain?', 'in dbms?'), you MUST select 'os' mode. Do not get confused by folder names that look like academic topics or acronyms.\n\n"
            "Respond ONLY with a raw JSON object in this format:\n"
            '{"mode": "friend", "needs_search": false, "reason": "reasoning here"}'
        )
        
        try:
            res_text = simple_query(message, system_prompt).strip()
            if res_text.startswith("```"):
                res_text = re.sub(r"^```json\s*", "", res_text)
                res_text = re.sub(r"\s*```$", "", res_text)
            
            data = json.loads(res_text)
            mode = data.get("mode", "friend").lower()
            needs_search = bool(data.get("needs_search", False))
            reason = data.get("reason", "Parsed LLM routing decision.")
            
            # Sanitize mode
            if mode not in ["friend", "mentor", "researcher", "coder", "os", "vision"]:
                mode = "friend"
                
            log_agent_action("Planner", f"Route decided: mode={mode}, search={needs_search}", reason)
            return {"mode": mode, "needs_search": needs_search, "reason": reason}
            
        except Exception as e:
            print(f"[Noor Planner] Planner routing failed: {e}. Falling back to heuristics.")
            from brain.personality import detect_mode
            from brain.search import needs_search as ddg_needs_search
            
            mode = detect_mode(message)
            req_search = ddg_needs_search(message)
            log_agent_action("Planner", f"Fallback routing: mode={mode}, search={req_search}", f"Error: {e}")
            return {"mode": mode, "needs_search": req_search, "reason": "Heuristics fallback."}


class ResearchAgent:
    """Agent that handles information lookup and summarization."""
    
    @staticmethod
    def gather_research(query: str) -> str:
        """Run web search and synthesize results into a concise brief."""
        log_agent_action("Researcher", f"Researching: '{query}'")
        
        try:
            results = web_search(query)
            if not results:
                log_agent_action("Researcher", "No results found.")
                return ""
            
            log_agent_action("Researcher", f"Found {len(results)} search results. Summarizing...")
            
            prompt = (
                f"User Query: {query}\n\n"
                "Search Results:\n" + "\n\n".join(results) + "\n\n"
                "Provide a bulleted list of key findings directly answering the query."
            )
            
            system_prompt = "You are Noor's Research Agent. Synthesize raw web search results into a concise factual brief."
            brief = simple_query(prompt, system_prompt)
            log_agent_action("Researcher", f"Research brief generated ({len(brief)} chars).")
            return brief
            
        except Exception as e:
            log_agent_action("Researcher", f"Research failed: {e}")
            return ""


class MemoryAgent:
    """Agent that extracts rules/corrections and maintains the Knowledge Graph."""
    
    @staticmethod
    def process_conversation_turn(user_msg: str, assistant_resp: str) -> None:
        """Extract user corrections and Knowledge Graph relations from the turn."""
        log_agent_action("MemoryGraph", "Analyzing turn for facts, corrections, and graph updates...")
        
        system_prompt = (
            "You are Noor's Memory and Knowledge Graph Agent. Analyze the user's message and the assistant's response.\n"
            "Extract any:\n"
            "1. Corrections/Rules: If the user corrects a mistake or sets a rule (e.g. 'No, my dog is Rex' or 'Remember that I dislike coffee'), "
            "extract the trigger 'pattern' (e.g. 'dog' or 'coffee') and the 'correction' statement (e.g. 'My dog is Rex' or 'I dislike coffee').\n"
            "2. Knowledge Graph Elements:\n"
            "   - nodes: Important entities mentioned (e.g. people, projects, hobbies, technologies).\n"
            "   - edges: Relationships between these nodes (e.g. 'Arshad' works_on 'Noor').\n"
            "     Relations should be short verbs (e.g. works_on, collaborator_of, member_of, has_goal, uses, belongs_to).\n\n"
            "Respond ONLY with a JSON object in this format (keep lists empty if nothing is found):\n"
            "{\n"
            '  "corrections": [ {"pattern": "dog", "correction": "My dog is Rex"} ],\n'
            '  "nodes": [ {"id": "arshad", "name": "Arshad", "type": "person"}, {"id": "noor", "name": "Noor", "type": "project"} ],\n'
            '  "edges": [ {"source_id": "arshad", "target_id": "noor", "relation": "works_on"} ]\n'
            "}"
        )
        
        prompt = f"User: {user_msg}\nAssistant: {assistant_resp}"
        
        try:
            res_text = simple_query(prompt, system_prompt).strip()
            if res_text.startswith("```"):
                res_text = re.sub(r"^```json\s*", "", res_text)
                res_text = re.sub(r"\s*```$", "", res_text)
                
            data = json.loads(res_text)
            
            # Save corrections
            corrections = data.get("corrections", [])
            for c in corrections:
                pat = c.get("pattern", "")
                corr = c.get("correction", "")
                if pat and corr:
                    save_correction(pat, corr)
                    log_agent_action("MemoryGraph", f"Saved correction rule: [{pat} => {corr}]")
            
            # Save Knowledge Graph elements
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            
            for n in nodes:
                n_id = n.get("id", "")
                name = n.get("name", "")
                n_type = n.get("type", "concept")
                if n_id and name:
                    add_graph_node(n_id, name, n_type)
                    log_agent_action("MemoryGraph", f"Graph Node added: {name} ({n_type})")
                    
            for e in edges:
                src = e.get("source_id", "")
                tgt = e.get("target_id", "")
                rel = e.get("relation", "")
                if src and tgt and rel:
                    add_graph_edge(src, tgt, rel)
                    log_agent_action("MemoryGraph", f"Graph Edge added: {src} ──[{rel}]──> {tgt}")
                    
        except Exception as e:
            print(f"[Noor MemoryGraph] Agent processing failed: {e}")
            log_agent_action("MemoryGraph", f"Processing failed: {e}")


def _resolve_path_from_history(message: str, history: list[dict] = None) -> str | None:
    """Scan history from newest to oldest to find the most recently mentioned path or folder alias."""
    msg_lower = message.lower().strip()
    
    # 1. First, check if message itself contains an explicit path/alias
    path_regex = r'\b[a-zA-Z]:\\[^"\n\r]*|\bdownloads\b|\bdesktop\b|\bdocuments\b|\bnoor\b'
    match = re.search(path_regex, message, re.IGNORECASE)
    if match:
        val = match.group(0).strip().strip('"').strip("'")
        if val:
            val_lower = val.lower()
            from brain.os_agent import FOLDER_MAP
            if val_lower in FOLDER_MAP:
                return FOLDER_MAP[val_lower]
            return val

    # 2. Extract potential subfolder name from current message (e.g. "what is in DBMS folder" -> "dbms")
    subfolder_candidate = None
    # Look for patterns like "[word] folder" or "folder [word]" or "inside [word]"
    msg_clean = msg_lower.replace('"', '').replace("'", "")
    match_folder = re.search(r'\b([\w\-]+)\s+folder\b', msg_clean)
    if match_folder:
        subfolder_candidate = match_folder.group(1).strip()
    else:
        match_inside = re.search(r'\b(?:inside|in)\s+([\w\-]+)\b', msg_clean)
        if match_inside:
            candidate = match_inside.group(1).strip()
            if candidate not in ["it", "this", "that", "here", "there", "my"]:
                subfolder_candidate = candidate

    # 3. Pronoun / history scanning
    pronouns = ["it", "this folder", "that folder", "here", "its", "folder"]
    if any(p in msg_lower for p in pronouns) or not msg_lower or subfolder_candidate:
        if history:
            for h in reversed(history):
                content = h["content"]
                base_path = None
                
                # Check for path in content
                match_hist = re.search(r'\b([a-zA-Z]:\\[^"\n\r]*)\b', content, re.IGNORECASE)
                if match_hist:
                    base_path = match_hist.group(1).strip().strip('"').strip("'")
                else:
                    match_quotes = re.search(r'["\']([a-zA-Z]:\\[^"\']+)["\']', content, re.IGNORECASE)
                    if match_quotes:
                        base_path = match_quotes.group(1).strip()
                    else:
                        for alias in ["downloads", "desktop", "documents", "noor", "project"]:
                            if alias in content.lower():
                                from brain.os_agent import FOLDER_MAP
                                base_path = FOLDER_MAP.get(alias)
                                break
                                
                if base_path:
                    # If we found a base path and we have a subfolder candidate
                    if subfolder_candidate:
                        import os
                        from brain.os_agent import FOLDER_MAP
                        if base_path.lower() in FOLDER_MAP:
                            base_path = FOLDER_MAP[base_path.lower()]
                        
                        # 1. Search case-insensitively in parent directory first, to match exact filesystem case
                        try:
                            parent_dir = os.path.abspath(base_path)
                            if os.path.isdir(parent_dir):
                                for name in os.listdir(parent_dir):
                                    if name.lower() == subfolder_candidate:
                                        return os.path.join(parent_dir, name)
                        except Exception:
                            pass
                            
                        # 2. Fallback to direct join
                        candidate_path = os.path.join(base_path, subfolder_candidate)
                        return os.path.abspath(candidate_path)
                            
                    return base_path
    return None


def _resolve_delete_path(message: str, history: list[dict] = None) -> tuple[str, bool]:
    """
    Extract the file path to be deleted and check if the deletion is confirmed.
    Returns (resolved_path, confirmed).
    """
    msg_lower = message.lower().strip()
    
    # 1. Check if the user is confirming a deletion
    confirmed = False
    confirm_words = ["yes", "confirm", "confirm delete", "delete it", "haan", "sure", "ok", "okay", "do it"]
    if msg_lower in confirm_words or any(w in msg_lower for w in ["yes delete", "confirm delete", "please delete", "do it"]):
        confirmed = True
        
    # If it is a confirmation, scan history for a pending delete warning
    if confirmed and history:
        for h in reversed(history):
            if h["role"] == "assistant" and "confirm that you want to delete" in h["content"]:
                match_path = re.search(r'want to delete\s+([^\n\r\t]+?)\.?$', h["content"])
                if match_path:
                    resolved_path = match_path.group(1).strip().strip('"').strip("'")
                    return resolved_path, True
                    
    # 2. Extract filename/path from quotes
    match_quotes = re.search(r'["\'“”‘’]([^"\'“”‘’]+)["\'“”‘’]', message)
    filename = None
    if match_quotes:
        filename = match_quotes.group(1).strip()
    else:
        # Match words ending in common extensions or containing dot
        match_ext = re.search(r'\b([\w\-]+\.(?:txt|png|jpg|jpeg|pdf|docx|xlsx|zip|csv|py|json|md))\b', msg_lower)
        if match_ext:
            filename = match_ext.group(1).strip()
            
    if filename:
        resolved_path = _resolve_file_path(message, history)
        return resolved_path, confirmed
        
    return "", confirmed


def _clean_message_for_keywords(message: str) -> str:
    """Strip quoted substrings and words with file extensions to prevent matching filenames as verbs."""
    import re
    msg_lower = message.lower().strip()
    # 1. Strip any quoted substrings (handles standard and smart quotes)
    msg_clean = re.sub(r'["\'“”‘’][^"\'“”‘’]+["\'“”‘’]', '', msg_lower)
    # 2. Strip any words ending in common extensions
    msg_clean = re.sub(r'\b[\w\-]+\.(?:txt|py|json|md|csv|png|jpg|jpeg|pdf|docx|xlsx|zip)\b', '', msg_clean)
    return msg_clean


def _resolve_file_path(message: str, history: list[dict] = None) -> str:
    """
    Robustly extract the target folder and filename from message and history,
    returning an absolute path.
    """
    import os
    import re
    msg_lower = message.lower().strip()
    
    # 1. Determine destination folder
    from brain.os_agent import FOLDER_MAP
    folder = FOLDER_MAP.get("noor") + "\\data"  # Default
    
    # helper for checking if the query explicitly targets the noor folder/project rather than just addressing the agent
    targets_noor_folder = "noor folder" in msg_lower or "project" in msg_lower or "/noor/" in msg_lower or "\\noor\\" in msg_lower or msg_lower.endswith("noor") or re.search(r'\bin\s+noor\b', msg_lower)
    
    if "desktop" in msg_lower:
        folder = FOLDER_MAP.get("desktop")
    elif "download" in msg_lower:
        folder = FOLDER_MAP.get("downloads")
    elif "document" in msg_lower:
        folder = FOLDER_MAP.get("documents")
    elif targets_noor_folder:
        folder = FOLDER_MAP.get("noor")
        
    # Try to find a base path from history if no folder is explicitly mentioned in current query
    has_explicit_folder = "desktop" in msg_lower or "download" in msg_lower or "document" in msg_lower or targets_noor_folder
    if not has_explicit_folder:
        hist_folder = None
        if history:
            for h in reversed(history):
                content = h["content"].lower()
                targets_hist_noor = "noor folder" in content or "project" in content or "/noor/" in content or "\\noor\\" in content or content.strip().endswith("noor") or re.search(r'\bin\s+noor\b', content)
                if "desktop" in content:
                    hist_folder = FOLDER_MAP.get("desktop")
                    break
                elif "download" in content:
                    hist_folder = FOLDER_MAP.get("downloads")
                    break
                elif "document" in content:
                    hist_folder = FOLDER_MAP.get("documents")
                    break
                elif targets_hist_noor:
                    hist_folder = FOLDER_MAP.get("noor")
                    break
                match_hist = re.search(r'\b([a-zA-Z]:\\[^"\n\r]*)\b', h["content"], re.IGNORECASE)
                if match_hist:
                    hist_folder = match_hist.group(1).strip().strip('"').strip("'")
                    break
        if hist_folder:
            folder = hist_folder
    else:
        hist_folder = _resolve_path_from_history(message, history)
        if hist_folder:
            folder = hist_folder
        
    # 2. Extract filename
    filename = None
    
    # Try to find word with extension: e.g. todo.txt, ac_repair_logo.png
    match_ext = re.search(r'\b([\w\-]+\.(?:txt|py|json|md|csv|png|jpg|jpeg|pdf|docx|xlsx|zip))\b', msg_lower)
    if match_ext:
        filename = match_ext.group(1)
    else:
        # Look for quoted filename
        match_quotes = re.search(r'["\'“”‘’]([\w\-]+\.\w+)["\'“”‘’]', message)
        if match_quotes:
            filename = match_quotes.group(1)
        else:
            # Look for patterns like "[word] name file" or "[word] file"
            match_word = re.search(r'\b([\w\-]+)\s*(?:naam ki|name|file|txt)\b', msg_lower)
            if match_word and match_word.group(1) not in ["create", "write", "save", "delete", "read", "edit", "new", "a", "this", "my"]:
                filename = f"{match_word.group(1)}.txt"
            elif "afsha" in msg_lower:
                filename = "afsha.txt"
            else:
                filename = "data.txt" # Default
                 
    return os.path.abspath(os.path.join(folder, filename))


def _extract_file_content(message: str) -> str:
    """
    Robustly extract text content meant for file writing/editing.
    """
    import re
    msg_lower = message.lower()
    
    # Check for dynamic expressions first
    if "today's date" in msg_lower or "todays date" in msg_lower or "today date" in msg_lower:
        import datetime
        return datetime.datetime.now().strftime("%Y-%m-%d")
        
    # 1. Look for content in quotes (single or double)
    match_quotes = re.search(r'["\'“”‘’]([^"\'“”‘’]+)["\'“”‘’]', message)
    if match_quotes:
        # Avoid matching the filename if the filename was also in quotes
        quoted_str = match_quotes.group(1)
        if not re.match(r'^[\w\-]+\.\w+$', quoted_str):
            return quoted_str
        # Check if there is a second quoted match
        matches = re.findall(r'["\'“”‘’]([^"\'“”‘’]+)["\'“”‘’]', message)
        for m in matches:
            if not re.match(r'^[\w\-]+\.\w+$', m):
                return m
        
    # 2. Look for keywords like "containing", "content", "with text"
    for marker in ["containing", "content is", "with text", "write", "save"]:
        if marker in msg_lower:
            parts = message.split(marker)
            if len(parts) > 1:
                # Strip common trailing filler
                content = parts[1].strip()
                # If it ends with "on desktop" or similar, strip it
                content_clean = re.sub(r'\b(?:on|in|to)\s+(?:desktop|downloads|documents|noor|project)\b.*$', '', content, flags=re.IGNORECASE).strip()
                if content_clean:
                    return content_clean
                    
    # 3. Fallback
    if "netflix" in msg_lower:
        return "netflix?"
    return "hello! world"


class OSAgent:
    """Agent that handles OS control and safe command execution."""
    
    @staticmethod
    def _detect_action_heuristically(message: str, history: list[dict] = None) -> dict | None:
        """
        Check if message matches a simple action pattern. If so, return the JSON action payload.
        This bypasses the LLM decision step and reduces latency dramatically.
        """
        import re
        msg_lower = message.lower().strip()
        
        # 0. Check if this is a confirmation for a pending file deletion
        path, confirmed = _resolve_delete_path(message, history)
        if confirmed and path:
            return {"type": "delete_file", "path": path, "confirmed": True}
        
        # 1. Directory listing / folder contents
        dir_triggers = [
            "how many files", "list files", "list folder", "contents of", "show files",
            "what is in", "what's in", "whats in", "what is inside", "what's inside", "whats inside",
            "mein kya hai", "mein kya hain", "me kya hai", "me kya hain", "kya hai", "kya hain",
            "directory", "folder"
        ]
        is_dir_request = (any(x in msg_lower for x in dir_triggers) or msg_lower.startswith("dir") or msg_lower.startswith("ls")) and not msg_lower.startswith(("open", "launch", "start"))
        if is_dir_request:
            path = _resolve_path_from_history(message, history)
            if not path:
                # Attempt to extract from message
                for word in message.split():
                    word_clean = word.strip('"').strip("'").strip("?").strip(",")
                    if "\\" in word_clean or "/" in word_clean or word_clean.lower() in ["downloads", "desktop", "documents", "noor"]:
                        path = word_clean
                        break
            if path:
                return {"type": "dir_list", "path": path}
            # Fallback path if we explicitly asked about files but couldn't resolve
            if "dir" in msg_lower or "ls" in msg_lower:
                return {"type": "dir_list", "path": "D:\\Noor"}

        # 2. Screenshot
        if any(x in msg_lower for x in ["screenshot", "screen shot", "screen capture", "capture screen"]):
            return {"type": "take_screenshot"}

        # 3. Radio state (Bluetooth, Wifi, Airplane mode)
        if "bluetooth" in msg_lower:
            if re.search(r"\b(on|enable|active)\b", msg_lower):
                return {"type": "toggle_radio", "radio": "bluetooth", "state": "on"}
            elif re.search(r"\b(off|disable)\b", msg_lower):
                return {"type": "toggle_radio", "radio": "bluetooth", "state": "off"}
            return {"type": "open_app", "target": "bluetooth"}

        if "wifi" in msg_lower or "wi-fi" in msg_lower:
            if re.search(r"\b(on|enable|active)\b", msg_lower):
                return {"type": "toggle_radio", "radio": "wifi", "state": "on"}
            elif re.search(r"\b(off|disable)\b", msg_lower):
                return {"type": "toggle_radio", "radio": "wifi", "state": "off"}
            return {"type": "open_app", "target": "wifi"}

        if "airplane" in msg_lower:
            airplane_state = "on"
            if re.search(r"\b(off|disable)\b", msg_lower):
                airplane_state = "off"
            return {"type": "toggle_radio", "radio": "airplane", "state": airplane_state}

        # 4. Open Application / Resource (URL, App, File, Folder, Settings)
        if re.search(r"\b(open|launch|start)\b", msg_lower):
            match = re.search(r"\b(?:open|launch|start)\s+(.+)$", msg_lower)
            target_candidate = match.group(1).strip() if match else msg_lower
            target_candidate = target_candidate.strip("?").strip(".").strip()

            try:
                from brain.resolvers.manager import ResourceResolverManager
                manager = ResourceResolverManager()
                resolved = manager.classify_and_resolve(target_candidate)
                if resolved and resolved.get("confidence", 0.0) >= 0.50:
                    return {"type": "open_app", "target": target_candidate}
            except Exception:
                pass

            return {"type": "open_app", "target": target_candidate}

        # 5. Disk Space
        if any(x in msg_lower for x in ["space", "khali", "disk", "usage"]):
            return {"type": "get_disk_space"}

        # 6. Clipboard
        if "clipboard" in msg_lower or "clip" in msg_lower:
            if any(x in msg_lower for x in ["copy", "write", "set"]):
                # Extract content to copy
                content = message
                for word in ["copy", "clipboard", "write", "set", "to"]:
                    content = re.sub(r'\b' + word + r'\b', '', content, flags=re.IGNORECASE)
                content = content.strip().strip('"').strip("'").strip()
                if content:
                    return {"type": "write_clipboard", "content": content}
            else:
                return {"type": "read_clipboard"}

        # 7. Close App
        if "close" in msg_lower or "exit" in msg_lower or "kill" in msg_lower:
            for app in ["notepad", "calculator", "calc", "paint", "mspaint", "chrome", "brave", "settings"]:
                if app in msg_lower:
                    return {"type": "close_app", "target": app}

        # 7.5. Active window / focused application
        if any(x in msg_lower for x in ["active window", "focused window", "current window", "focused app", "active app", "current app", "focused application", "active application"]):
            return {"type": "get_active_window"}

        # 7.6. Switch window / app
        if "switch" in msg_lower or "bring to foreground" in msg_lower:
            target = None
            for app in ["notepad", "calculator", "calc", "paint", "mspaint", "chrome", "brave", "settings", "explorer"]:
                if app in msg_lower:
                    target = app
                    break
            if not target:
                match_switch = re.search(r'\bswitch\s+(?:to\s+)?([\w\-]+)\b', msg_lower)
                if match_switch and match_switch.group(1) not in ["window", "app"]:
                    target = match_switch.group(1)
            if target:
                return {"type": "switch_window", "target": target}

        # 8. File Operations (write/create/read/delete/search)
        msg_clean = _clean_message_for_keywords(message)

        # Delete file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["delete", "remove"]):
            path, confirmed = _resolve_delete_path(message, history)
            if not path:
                path = _resolve_file_path(message, history)
                confirmed = "yes" in msg_clean or "confirm" in msg_clean or "delete it" in msg_clean
            return {"type": "delete_file", "path": path, "confirmed": confirmed}

        # Edit/Append file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["edit", "append", "add"]):
            path = _resolve_file_path(message, history)
            content = _extract_file_content(message)
            append = "append" in msg_clean or "add" in msg_clean
            return {"type": "edit_file", "path": path, "content": content, "append": append}

        # Read file / summarize file trigger
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["read", "padho", "show file", "summarize", "summary"]):
            from brain.os_agent import FOLDER_MAP
            # Resolve directory first if no filename extension or quote is found
            has_filename = False
            match_ext = re.search(r'\b([\w\-]+\.(?:txt|py|json|md|csv|png|jpg|jpeg|pdf|docx|xlsx|zip))\b', msg_lower)
            match_quotes = re.search(r'["\']([\w\-]+\.\w+)["\']', message)
            if match_ext or match_quotes:
                has_filename = True
                
            path = None
            if not has_filename:
                if "desktop" in msg_clean:
                    path = FOLDER_MAP.get("desktop")
                elif "download" in msg_clean:
                    path = FOLDER_MAP.get("downloads")
                elif "document" in msg_clean:
                    path = FOLDER_MAP.get("documents")
                elif "noor" in msg_clean or "project" in msg_clean:
                    path = FOLDER_MAP.get("noor")
                else:
                    path = _resolve_path_from_history(message, history)
            
            if not path:
                path = _resolve_file_path(message, history)
                
            if path:
                import os
                path_resolved = os.path.abspath(path)
                if os.path.isdir(path_resolved):
                    try:
                        files = sorted(os.listdir(path_resolved), key=lambda x: x.lower())
                        target_file = None
                        for f in files:
                            if "pdf" in msg_clean:
                                if f.lower().endswith(".pdf"):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                            else:
                                if f.lower().endswith((".pdf", ".txt")):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                        if not target_file:
                            for f in files:
                                if f.lower().endswith((".pdf", ".txt")):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                        if target_file:
                            path = os.path.abspath(target_file)
                    except Exception:
                        pass
            return {"type": "read_file", "path": path}

        # Create/Write file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["save", "write", "create", "likh"]):
            path = _resolve_file_path(message, history)
            content = _extract_file_content(message)
            open_after = "open" in msg_clean or "notepad" in msg_clean
            return {"type": "write_file", "path": path, "content": content, "open_after": open_after}

        # File Search
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["find", "search file", "where is"]):
            query = message
            for term in ["find my", "find the", "find", "search file", "search files for", "search for", "where is my", "where is the", "where is"]:
                if query.lower().startswith(term):
                    query = query[len(term):].strip()
                    break
            query = query.strip("?").strip(".").strip().strip('"').strip("'")
            if query:
                return {"type": "file_search", "query": query}

        return None

    @staticmethod
    def run_stream(message: str, history: list[dict] = None) -> Generator[str, None, None]:
        """
        Execute OS Agent in an autonomous ReAct loop.
        Decides actions sequentially, runs them, formats logs, and streams the final conversational synthesis.
        """
        log_agent_action("OSAgent", f"Running autonomous OS Agent loop for: '{message}'")
        executed_actions = []
        
        # Max steps in the loop
        max_steps = 4
        
        # Clean history context
        history_context = ""
        if history:
            history_context = "\nRecent Conversation History:\n"
            for h in history:
                role = "User" if h["role"] == "user" else "Assistant"
                content = h["content"]
                if len(content) > 300:
                    content = content[:300] + "..."
                history_context += f"{role}: {content}\n"
 
        # Try heuristic detection first to bypass LLM action decision and reduce latency by 50-80%
        heuristic_action = OSAgent._detect_action_heuristically(message, history)
        if heuristic_action:
            action_type = heuristic_action.get("type", "")
            norm_type = action_type.lower().strip()
            
            # Format user log
            log_msg = ""
            if norm_type == "dir_list":
                p = heuristic_action.get("path") or "current folder"
                log_msg = f"⚙️ *OS Agent:* Listing directory: `{p}`...\n\n"
            elif norm_type == "open_app":
                t = heuristic_action.get("target") or "app"
                log_msg = f"⚙️ *OS Agent:* Opening: `{t}`...\n\n"
            elif norm_type == "command":
                c = heuristic_action.get("target") or "command"
                log_msg = f"⚙️ *OS Agent:* Running command: `{c}`...\n\n"
            elif norm_type == "read_file":
                p = heuristic_action.get("path") or "file"
                log_msg = f"⚙️ *OS Agent:* Reading file: `{p}`...\n\n"
            elif norm_type == "write_file":
                p = heuristic_action.get("path") or "file"
                log_msg = f"⚙️ *OS Agent:* Creating file: `{p}`...\n\n"
            elif norm_type == "edit_file":
                p = heuristic_action.get("path") or "file"
                log_msg = f"⚙️ *OS Agent:* Editing file: `{p}`...\n\n"
            elif norm_type == "delete_file":
                p = heuristic_action.get("path") or "file"
                log_msg = f"⚙️ *OS Agent:* Requesting file deletion: `{p}`...\n\n"
            elif norm_type == "take_screenshot":
                log_msg = "⚙️ *OS Agent:* Taking screenshot...\n\n"
            elif norm_type == "get_active_window":
                log_msg = "⚙️ *OS Agent:* Checking active window...\n\n"
            elif norm_type == "read_clipboard":
                log_msg = "⚙️ *OS Agent:* Checking clipboard...\n\n"
            elif norm_type == "write_clipboard":
                log_msg = "⚙️ *OS Agent:* Copying to clipboard...\n\n"
            elif norm_type == "toggle_radio":
                r = heuristic_action.get("radio") or "device"
                s = heuristic_action.get("state") or "state"
                log_msg = f"⚙️ *OS Agent:* Toggling {r} {s}...\n\n"
            elif norm_type == "file_search":
                q = heuristic_action.get("query") or "file"
                log_msg = f"⚙️ *OS Agent:* Searching files for: `{q}`...\n\n"
            else:
                log_msg = f"⚙️ *OS Agent:* Running action `{action_type}`...\n\n"
                
            yield log_msg
            
            # Execute action
            try:
                result = OSAgent._execute_action(heuristic_action, message, history)
                executed_actions.append({"action": heuristic_action, "result": result})
                
                # Check if this requires synthesis
                synthesis_keywords = ["tell me", "describe", "what is on", "what's on", "summarize", "summary", "explain", "what does", "analyse", "analysis"]
                if any(kw in message.lower() for kw in synthesis_keywords):
                    for token in OSAgent._stream_synthesis(message, executed_actions, history_context):
                        yield token
                else:
                    # Directly yield the raw result for instant execution and perfect conciseness
                    yield result
                return
            except Exception as he_err:
                log_agent_action("OSAgent", f"Heuristic execution failed: {he_err}. Falling back to ReAct loop.")

        for step in range(max_steps):
            # Format system prompt for action decision
            system_prompt = (
                "You are Noor's OS Control Agent. Your goal is to decide and perform system actions to fulfill the user's request.\n"
                "You can execute actions one by one. After each action, you will receive the result and can decide on the next action or finish with a final response.\n\n"
                "Available Action Types:\n"
                "- type='open_app', target='notepad' | 'calc' | 'paint' | 'explorer' | 'chrome' | 'brave' | 'control' | 'settings' | 'bluetooth' | 'wifi' | 'sound' | 'downloads' | 'desktop' | 'noor' | 'folder path'\n"
                "- type='command', target='dir D:\\Noor' | 'ipconfig'\n"
                "- type='write_file', path='path', content='text', open_after=true/false\n"
                "- type='get_active_window'\n"
                "- type='read_clipboard'\n"
                "- type='write_clipboard', content='text'\n"
                "- type='close_app', target='notepad' | ...\n"
                "- type='switch_window', target='window title substring'\n"
                "- type='show_notification', title='title', content='msg'\n"
                "- type='get_disk_space'\n"
                "- type='read_file', path='path'\n"
                "- type='edit_file', path='path', content='text', append=true/false\n"
                "- type='delete_file', path='path', confirmed=true/false\n"
                "- type='take_screenshot'\n"
                "- type='toggle_radio', radio='bluetooth' | 'wifi' | 'airplane', state='on' | 'off'\n"
                "- type='dir_list', path='folder path'\n"
                "- type='respond', content='Your message to the user explaining what you did and what you found.'\n\n"
                "IMPORTANT RULES:\n"
                "1. If you need to list files or see what is inside a folder, choose type='dir_list'. Set path to the target folder (e.g. 'DBMS' or the resolved path).\n"
                "2. Do not use action types not listed here (e.g., do not use 'list_directory' or 'run_shell_command').\n"
                "3. Respond ONLY with a raw JSON object matching the chosen action type. No backticks, no extra text.\n\n"
                "Examples:\n"
                '{"type": "dir_list", "path": "downloads"}\n'
                '{"type": "open_app", "target": "notepad"}\n'
                '{"type": "command", "target": "ipconfig"}\n'
                '{"type": "respond", "content": "Here is what I found..."}'
            )
            
            # Format the scratchpad of actions executed in this loop
            scratchpad = ""
            if executed_actions:
                scratchpad = "\nSystem Actions Executed in this Turn:\n"
                for idx, act in enumerate(executed_actions):
                    scratchpad += f"Step {idx+1}:\n"
                    scratchpad += f"  - Action decided: {json.dumps(act['action'])}\n"
                    res_summary = act['result']
                    if len(res_summary) > 500:
                        res_summary = res_summary[:500] + "...\n[Truncated]"
                    scratchpad += f"  - Result: {res_summary}\n"

            prompt_input = f"{history_context}\nCurrent User Message: {message}\n{scratchpad}\nNext Action (respond ONLY in JSON):"

            try:
                res_text = simple_query(prompt_input, system_prompt).strip()
                if res_text.startswith("```"):
                    res_text = re.sub(r"^```json\s*", "", res_text)
                    res_text = re.sub(r"\s*```$", "", res_text)
                
                data = json.loads(res_text)
                action_type = data.get("type", "")
                
                # Normalize synonym types before routing check
                norm_type = action_type.lower().strip()
                if norm_type in ["list_directory", "list_dir", "dir"]:
                    norm_type = "dir_list"
                elif norm_type in ["respond", "response"]:
                    norm_type = "respond"

                if norm_type == "respond":
                    # Directly stream the final response synthesis using LLM for natural dialogue
                    for token in OSAgent._stream_synthesis(message, executed_actions, history_context):
                        yield token
                    break
                
                # Format nice user logs
                log_msg = ""
                if norm_type == "dir_list":
                    p = data.get("path") or "current folder"
                    log_msg = f"⚙️ *OS Agent:* Listing directory: `{p}`...\n\n"
                elif norm_type == "open_app":
                    t = data.get("target") or "app"
                    log_msg = f"⚙️ *OS Agent:* Opening: `{t}`...\n\n"
                elif norm_type == "command":
                    c = data.get("target") or "command"
                    log_msg = f"⚙️ *OS Agent:* Running command: `{c}`...\n\n"
                elif norm_type == "read_file":
                    p = data.get("path") or "file"
                    log_msg = f"⚙️ *OS Agent:* Reading file: `{p}`...\n\n"
                elif norm_type == "write_file":
                    p = data.get("path") or "file"
                    log_msg = f"⚙️ *OS Agent:* Creating file: `{p}`...\n\n"
                elif norm_type == "edit_file":
                    p = data.get("path") or "file"
                    log_msg = f"⚙️ *OS Agent:* Editing file: `{p}`...\n\n"
                elif norm_type == "delete_file":
                    p = data.get("path") or "file"
                    log_msg = f"⚙️ *OS Agent:* Requesting file deletion: `{p}`...\n\n"
                elif norm_type == "take_screenshot":
                    log_msg = "⚙️ *OS Agent:* Taking screenshot...\n\n"
                elif norm_type == "get_active_window":
                    log_msg = "⚙️ *OS Agent:* Checking active window...\n\n"
                elif norm_type == "read_clipboard":
                    log_msg = "⚙️ *OS Agent:* Checking clipboard...\n\n"
                elif norm_type == "write_clipboard":
                    log_msg = "⚙️ *OS Agent:* Copying to clipboard...\n\n"
                elif norm_type == "toggle_radio":
                    r = data.get("radio") or "device"
                    s = data.get("state") or "state"
                    log_msg = f"⚙️ *OS Agent:* Toggling {r} {s}...\n\n"
                else:
                    log_msg = f"⚙️ *OS Agent:* Running action `{action_type}`...\n\n"
                
                yield log_msg
                
                # Execute action
                result = OSAgent._execute_action(data, message, history)
                executed_actions.append({"action": data, "result": result})
                
                # Direct streaming synthesis for single-turn operations to reduce latency by 50%
                single_turn_types = ["dir_list", "read_file", "get_disk_space", "read_clipboard", "get_active_window", "toggle_radio", "take_screenshot", "open_app", "show_notification", "write_file", "edit_file", "delete_file", "close_app", "switch_window", "file_search"]
                if norm_type in single_turn_types:
                    for token in OSAgent._stream_synthesis(message, executed_actions, history_context):
                        yield token
                    break
                
            except Exception as e:
                log_agent_action("OSAgent", f"Action loop error: {e}")
                # Fallback to legacy parsing
                fallback_res = OSAgent.run_fallback_legacy(message, history, e)
                yield fallback_res
                break
        else:
            # Reached max steps without responding. Do a final synthesis stream.
            yield "\n⚙️ *OS Agent:* Synthesizing final response...\n\n"
            for token in OSAgent._stream_synthesis(message, executed_actions, history_context):
                yield token

    @staticmethod
    def run(message: str, history: list[dict] = None) -> str:
        """Parse request and execute OS commands sequentially, returning the final response."""
        tokens = list(OSAgent.run_stream(message, history))
        return "".join(tokens)

    @staticmethod
    def _execute_action(data: dict, message: str, history: list[dict] = None) -> str:
        action_type = data.get("type", "").lower().strip()
        target = data.get("target", "")
        
        # Standardize action type synonyms
        if action_type in ["list_directory", "list_dir", "dir"]:
            action_type = "dir_list"
        elif action_type in ["run_shell_command", "shell_command", "run_command", "exec"]:
            action_type = "command"
        elif action_type in ["open_application", "open", "launch"]:
            action_type = "open_app"
        elif action_type in ["read_file_contents", "read"]:
            action_type = "read_file"
        elif action_type in ["write_file_contents", "write", "create_file"]:
            action_type = "write_file"
        elif action_type in ["edit_file_contents", "edit"]:
            action_type = "edit_file"
        elif action_type in ["delete_file_contents", "delete"]:
            action_type = "delete_file"
        elif action_type in ["search_files", "search_file", "find_file", "find_files", "search"]:
            action_type = "file_search"
            
        if action_type == "open_app" and target:
            from brain.os_agent import open_app
            return open_app(target)
        elif action_type == "file_search":
            query = data.get("query")
            if not query:
                return "⚠️ [OSAgent] No search query specified."
            from brain.os_agent import search_local_files
            return search_local_files(query)
        elif action_type == "command" and target:
            from brain.os_agent import execute_safe_command
            return execute_safe_command(target)
        elif action_type == "write_file":
            path = data.get("path", "data.txt")
            content = data.get("content", "")
            open_after = bool(data.get("open_after", False))
            from brain.os_agent import safe_write_file
            return safe_write_file(path, content, open_after)
        elif action_type == "get_active_window":
            from brain.os_agent import get_active_window_title
            return get_active_window_title()
        elif action_type == "read_clipboard":
            from brain.os_agent import get_clipboard_text
            text = get_clipboard_text()
            if not text:
                return "Clipboard is empty or contains non-text content."
            return text
        elif action_type == "write_clipboard":
            content = data.get("content", "")
            if not content:
                return "⚠️ [OSAgent] No content specified to write to clipboard."
            from brain.os_agent import set_clipboard_text
            ok = set_clipboard_text(content)
            if ok:
                return f"✅ Copied to clipboard: '{content}'"
            return "❌ Failed to copy to clipboard."
        elif action_type == "close_app" and target:
            from brain.os_agent import close_whitelisted_app
            return close_whitelisted_app(target)
        elif action_type == "switch_window" and target:
            from brain.os_agent import switch_to_window
            return switch_to_window(target)
        elif action_type == "show_notification":
            title = data.get("title", "Noor Notification")
            content = data.get("content") or data.get("message") or "Hello!"
            from brain.os_agent import show_desktop_notification
            return show_desktop_notification(title, content)
        elif action_type == "get_disk_space":
            from brain.os_agent import get_disk_space
            return get_disk_space()
        elif action_type == "read_file":
            path = data.get("path")
            if not path:
                return "⚠️ [OSAgent] No file path specified to read."
            from brain.os_agent import safe_read_file
            return safe_read_file(path)
        elif action_type == "edit_file":
            path = data.get("path")
            content = data.get("content", "")
            append = bool(data.get("append", False))
            if not path:
                return "⚠️ [OSAgent] No file path specified to edit."
            from brain.os_agent import safe_edit_file
            return safe_edit_file(path, content, append)
        elif action_type == "delete_file":
            path = data.get("path")
            confirmed = bool(data.get("confirmed", False))
            if not path:
                return "⚠️ [OSAgent] No file path specified to delete."
            
            # Double-check confirmation to prevent LLM from bypassing confirmation on first turn
            if confirmed:
                confirm_words = ["yes", "confirm", "haan", "sure", "ok", "okay", "do it", "delete it"]
                current_msg_lower = message.lower().strip()
                if not any(cw in current_msg_lower for cw in confirm_words) or any(ext in current_msg_lower for ext in [".png", ".txt", ".pdf", ".jpg", ".jpeg", ".docx", ".zip"]):
                    confirmed = False
                    
            from brain.os_agent import safe_delete_file
            return safe_delete_file(path, confirmed)
        elif action_type == "take_screenshot":
            from brain.vision import take_screenshot
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("D:\\Noor\\data", exist_ok=True)
            path = f"D:\\Noor\\data\\screenshot_{timestamp}.png"
            res = take_screenshot(path)
            if res.startswith("❌"):
                return res
            return f"✅ Screenshot taken and saved to {path}."
        elif action_type == "toggle_radio":
            radio = data.get("radio", "").lower()
            state = data.get("state", "").lower()
            if not radio or not state:
                return "⚠️ [OSAgent] Missing radio name or state."
            ps_state = "On" if state in ["on", "enable", "active"] else "Off"
            from brain.os_agent import set_radio_state, toggle_airplane_mode
            if radio == "bluetooth":
                return set_radio_state("Bluetooth", ps_state)
            elif radio in ["wifi", "wi-fi"]:
                return set_radio_state("WiFi", ps_state)
            elif radio == "airplane":
                airplane_state = "On" if state in ["on", "enable", "active"] else "Off"
                return toggle_airplane_mode(airplane_state)
            else:
                return f"⚠️ [OSAgent] Unknown radio type: {radio}"
        elif action_type == "dir_list":
            path = data.get("path")
            if not path:
                path = _resolve_path_from_history(message, history) or "D:\\Noor"
            from brain.os_agent import get_dir_list
            return get_dir_list(path)
        else:
            return "⚠️ [OSAgent] Could not understand the OS control action to perform."

    @staticmethod
    def _stream_synthesis(message: str, executed_actions: list, history_context: str) -> Generator[str, None, None]:
        """Synthesize a friendly final response based on the executed actions and their results."""
        executed_str = ""
        if executed_actions:
            executed_str = "\nSystem Actions Executed:\n"
            for idx, act in enumerate(executed_actions):
                executed_str += f"Step {idx+1}:\n"
                executed_str += f"  - Action decided: {json.dumps(act['action'])}\n"
                executed_str += f"  - Result: {act['result']}\n"
                
        system_prompt = (
            "You are Noor, Arshad's personal AI companion in OS Mode.\n"
            "You have just executed system activities to fulfill the user's request.\n"
            "Provide an extremely concise, direct response in Hinglish/English. State exactly what you did, and present all names of files/folders, command results, and status indicators (like ✅ or ❌) clearly without any unnecessary conversational filler or over-explaining.\n"
            "Speak directly to Arshad. Keep it brief and to the point."
        )
        
        prompt = (
            f"{history_context}\n"
            f"The user asked: '{message}'\n\n"
            f"{executed_str}\n"
            "Write your final response to Arshad:"
        )
        
        from brain.llm import get_gemini_client, call_groq_stream, call_openrouter_stream, FAST_MODEL
        import ollama
        import os
        from google.genai import types

        # Gemini
        gemini_client = get_gemini_client()
        if gemini_client:
            try:
                gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                )
                response_stream = gemini_client.models.generate_content_stream(
                    model=gemini_model_name,
                    contents=prompt,
                    config=config
                )
                for chunk in response_stream:
                    if chunk.text:
                        yield chunk.text
                return
            except Exception as e:
                print(f"[Noor OS Synthesis] Gemini failed: {e}")

        # Groq
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if groq_api_key:
            try:
                groq_model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-specdec")
                messages_payload = [{"role": "user", "content": prompt}]
                stream_generator = call_groq_stream(
                    messages=messages_payload,
                    model=groq_model_name,
                    system_instruction=system_prompt
                )
                for token in stream_generator:
                    yield token
                return
            except Exception as e:
                print(f"[Noor OS Synthesis] Groq failed: {e}")

        # OpenRouter
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        if openrouter_api_key:
            try:
                openrouter_model_name = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash")
                messages_payload = [{"role": "user", "content": prompt}]
                stream_generator = call_openrouter_stream(
                    messages=messages_payload,
                    model=openrouter_model_name,
                    system_instruction=system_prompt
                )
                for token in stream_generator:
                    yield token
                return
            except Exception as e:
                print(f"[Noor OS Synthesis] OpenRouter failed: {e}")

        # Local Ollama
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            stream_iter = ollama.chat(
                model=FAST_MODEL,
                messages=messages,
                stream=True
            )
            for chunk in stream_iter:
                token = chunk["message"]["content"]
                if token:
                    yield token
        except Exception as e:
            yield f"⚠️ [Noor OS Synthesis Error] Local Ollama failed: {e}"

    @staticmethod
    def run_fallback_legacy(message: str, history: list[dict], exception: Exception) -> str:
        """Fallback to simple heuristics parsing if ReAct loop fails."""
        from brain.os_agent import (
            open_app, get_disk_space, get_clipboard_text, set_clipboard_text,
            safe_write_file, safe_read_file, safe_edit_file, safe_delete_file,
            set_radio_state, toggle_airplane_mode, get_dir_list, search_local_files
        )
        msg_lower = message.lower()
        msg_clean = _clean_message_for_keywords(message)
        
        # 1. Directory listing
        if any(x in msg_clean for x in ["how many files", "list files", "list folder", "contents of", "show files", "what is in", "what's in", "whats in", "what is inside", "what's inside", "whats inside"]) or msg_lower.startswith("dir") or msg_lower.startswith("ls"):
            path = _resolve_path_from_history(message, history)
            if not path:
                for word in message.split():
                    word_clean = word.strip('"').strip("'")
                    if "\\" in word_clean or "/" in word_clean or word_clean.lower() in ["downloads", "desktop", "documents", "noor"]:
                        path = word_clean
                        break
            if not path:
                path = "D:\\Noor"
            return get_dir_list(path)
            
        # 2. Screenshot
        if "screenshot" in msg_clean or "screen shot" in msg_clean or "screen capture" in msg_clean or "capture screen" in msg_clean:
            from brain.vision import take_screenshot
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            os.makedirs("D:\\Noor\\data", exist_ok=True)
            path = f"D:\\Noor\\data\\screenshot_{timestamp}.png"
            res = take_screenshot(path)
            if res.startswith("❌"):
                return res
            return f"✅ Screenshot taken and saved to {path}."
            
        # 3. Radio state
        if "bluetooth" in msg_clean:
            if re.search(r"\b(on|enable|active)\b", msg_clean):
                return set_radio_state("Bluetooth", "On")
            elif re.search(r"\b(off|disable)\b", msg_clean):
                return set_radio_state("Bluetooth", "Off")
            return open_app("bluetooth")
            
        if "wifi" in msg_clean or "wi-fi" in msg_clean:
            if re.search(r"\b(on|enable|active)\b", msg_clean):
                return set_radio_state("WiFi", "On")
            elif re.search(r"\b(off|disable)\b", msg_clean):
                return set_radio_state("WiFi", "Off")
            return open_app("wifi")
            
        if "airplane" in msg_clean:
            airplane_state = "On"
            if re.search(r"\b(off|disable)\b", msg_clean):
                airplane_state = "Off"
            return toggle_airplane_mode(airplane_state)
            
        # 4. Open Application / Resource (URLs, Apps, Files, Folders, Settings)
        if re.search(r"\b(open|launch|start)\b", msg_clean):
            match = re.search(r"\b(?:open|launch|start)\s+(.+)$", msg_clean)
            target = match.group(1).strip() if match else msg_clean
            return open_app(target)

        # 5. File Operations (reordered and safe)
        # Delete file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["delete", "remove"]):
            path, confirmed = _resolve_delete_path(message, history)
            if not path:
                path = _resolve_file_path(message, history)
                confirmed = "yes" in msg_clean or "confirm" in msg_clean or "delete it" in msg_clean
            return safe_delete_file(path, confirmed)
            
        # Edit/Append file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["edit", "append", "add"]):
            path = _resolve_file_path(message, history)
            content = _extract_file_content(message)
            append = "append" in msg_clean or "add" in msg_clean
            return safe_edit_file(path, content, append)
            
        # Read file / summarize
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["read", "padho", "show", "summarize", "summary"]):
            path = _resolve_file_path(message, history)
            if path:
                import os
                path_resolved = os.path.abspath(path)
                if os.path.isdir(path_resolved):
                    try:
                        files = sorted(os.listdir(path_resolved), key=lambda x: x.lower())
                        target_file = None
                        for f in files:
                            if "pdf" in msg_clean:
                                if f.lower().endswith(".pdf"):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                            else:
                                if f.lower().endswith((".pdf", ".txt")):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                        if not target_file:
                            for f in files:
                                if f.lower().endswith((".pdf", ".txt")):
                                    target_file = os.path.join(path_resolved, f)
                                    break
                        if target_file:
                            path = os.path.abspath(target_file)
                    except Exception:
                        pass
            return safe_read_file(path)
            
        # Create/Write file
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["save", "write", "create", "likh"]):
            path = _resolve_file_path(message, history)
            content = _extract_file_content(message)
            open_after = "open" in msg_clean or "notepad" in msg_clean
            return safe_write_file(path, content, open_after)

        # File Search
        if any(re.search(r'\b' + x + r'\b', msg_clean) for x in ["find", "search file", "where is"]):
            query = message
            for term in ["find my", "find the", "find", "search file", "search files for", "search for", "where is my", "where is the", "where is"]:
                if query.lower().startswith(term):
                    query = query[len(term):].strip()
                    break
            query = query.strip("?").strip(".").strip().strip('"').strip("'")
            if query:
                return search_local_files(query)
                
 
                    
        # 6. Disk space
        if "space" in msg_clean or "khali" in msg_clean or "disk" in msg_clean:
            return get_disk_space()
            
        # 7. Clipboard
        if "clipboard" in msg_clean or "clip" in msg_clean:
            if any(x in msg_clean for x in ["copy", "write", "set"]):
                content = message
                for word in ["copy", "clipboard", "write", "set", "to"]:
                    content = re.sub(r'\b' + word + r'\b', '', content, flags=re.IGNORECASE)
                content = content.strip().strip('"').strip("'").strip()
                if content:
                    ok = set_clipboard_text(content)
                    if ok:
                        return f"✅ Copied to clipboard: '{content}'"
                return "⚠️ [OSAgent] No text content found to copy to clipboard."
            else:
                text = get_clipboard_text()
                if not text:
                    return "Clipboard is empty or contains non-text content."
                return text
                
        return f"❌ [OSAgent Error] Failed to parse and execute OS command: {exception}"


class VisionAgent:
    """Agent that handles screen capture and image analysis."""
    
    @staticmethod
    def run(message: str, image_path: str = None) -> str:
        """Capture screen or describe the specified image based on query."""
        log_agent_action("VisionAgent", f"Analyzing vision request: '{message}'")
        
        from brain.vision import take_screenshot, analyze_image
        
        if not image_path:
            # Take screenshot automatically if none is provided
            image_path = take_screenshot()
            if image_path.startswith("❌"):
                return image_path
                
        # Stage 1: Get the visual description in English (to prevent confusing small local vision models)
        log_agent_action("VisionAgent", "Perceiving image content...")
        description = analyze_image(image_path, "Describe this image in detail.")
        
        if not description or description.startswith("❌") or description.startswith("⚠️"):
            # Return description directly if there was an error
            if not description:
                return "⚠️ [Vision Error] Local vision model returned an empty description. Please try again."
            return description
            
        # Stage 2: Formulate conversational Hinglish response using the main text LLM pipeline
        log_agent_action("VisionAgent", "Formulating final response using text model...")
        
        from brain.llm import simple_query
        
        system_prompt = (
            "You are Noor, Arshad's personal AI companion. Use the provided visual description of "
            "his screen/image to answer his question. Reply in natural, conversational English.\n\n"
            f"Visual Content Description:\n{description}"
        )
        
        final_response = simple_query(message, system_prompt)
        return final_response
