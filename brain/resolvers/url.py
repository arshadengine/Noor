"""
brain/resolvers/url.py
─────────────────────────────────────────────────────
URL & Smart Dev-Server Resource Resolver.
Recognizes localhost, IP addresses, IPv6, hostnames, popular web services (GitHub, Google, ChatGPT),
domain names, embedded domain URLs in sentences ("open taskas.tech in edge"), and dev server sockets.
Normalizes missing schemes and auto-detects active development server ports via psutil.
"""

import re
import psutil
from typing import Dict, Any
from brain.resolvers.base import BaseResourceResolver, ResourceType


class URLResolver(BaseResourceResolver):
    """Resource resolver for URLs, web services, domains, IP addresses, and local dev servers."""

    COMMON_DEV_PORTS = [3000, 5173, 8000, 8080, 5000, 8081, 4200, 3001, 8001]
    TLDS = [".com", ".org", ".net", ".io", ".dev", ".ai", ".app", ".co", ".in", ".edu", ".gov", ".me", ".tech"]
    
    WEB_SERVICES = {
        "github": "https://github.com",
        "google": "https://google.com",
        "youtube": "https://youtube.com",
        "twitter": "https://twitter.com",
        "x": "https://x.com",
        "linkedin": "https://linkedin.com",
        "chatgpt": "https://chatgpt.com",
        "openai": "https://openai.com",
        "reddit": "https://reddit.com",
        "gmail": "https://mail.google.com",
        "outlook": "https://outlook.live.com",
        "stackoverflow": "https://stackoverflow.com",
        "wikipedia": "https://wikipedia.org",
        "amazon": "https://amazon.com",
    }

    def match(self, target: str) -> float:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        # Popular Web Services (github, google, chatgpt)
        if t_clean in self.WEB_SERVICES or any(s in t_clean for s in self.WEB_SERVICES):
            return 0.99

        # Explicit schemes
        if t_clean.startswith(("http://", "https://", "ftp://")):
            return 1.0

        # Embedded domain extraction (e.g., "taskas.tech this url in edge")
        domain_match = re.search(r"\b([a-zA-Z0-9\-]+\.(?:tech|com|org|net|io|dev|ai|app|co|in|edu|gov|me))\b", t_clean)
        if domain_match:
            return 0.98

        # Localhost & Loopback IP patterns
        if any(x in t_clean for x in ["localhost", "127.0.0.1", "::1", "0.0.0.0"]):
            return 0.98

        # LAN IPs (192.168.x.x or 10.x.x.x)
        if re.search(r"\b(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?\b", t_clean):
            return 0.95

        # Domain names with TLDs
        if any(t_clean.endswith(tld) or f"{tld}/" in t_clean or f"{tld}:" in t_clean for tld in self.TLDS):
            return 0.95

        # Local dev hostnames
        if t_clean.endswith(".local") or re.search(r"^[\w\-]+\:\d{2,5}$", t_clean):
            return 0.90

        return 0.0

    def resolve(self, target: str) -> Dict[str, Any]:
        t_clean = target.lower().strip()
        if t_clean.startswith("open "):
            t_clean = t_clean[5:].strip()

        confidence = self.match(target)
        active_dev_ports = self._scan_active_dev_ports()

        # Check if user specified a target browser (edge, chrome, brave, firefox)
        target_browser = None
        for b in ["edge", "msedge", "chrome", "brave", "firefox"]:
            if b in t_clean:
                target_browser = b
                break

        # Handle popular web service aliases (github -> https://github.com)
        for ws_key, ws_url in self.WEB_SERVICES.items():
            if ws_key in t_clean:
                return {
                    "resource_type": ResourceType.URL,
                    "confidence": 0.99,
                    "resolved_target": ws_url,
                    "action": "open_url",
                    "metadata": {"service": ws_key, "browser": target_browser}
                }

        # Handle embedded domain in sentence ("taskas.tech this url in edge")
        domain_match = re.search(r"\b([a-zA-Z0-9\-]+\.(?:tech|com|org|net|io|dev|ai|app|co|in|edu|gov|me))\b", t_clean)
        if domain_match:
            raw_domain = domain_match.group(1)
            url = f"https://{raw_domain}"
            return {
                "resource_type": ResourceType.URL,
                "confidence": 0.98,
                "resolved_target": url,
                "action": "open_url",
                "metadata": {"domain": raw_domain, "browser": target_browser}
            }

        normalized_url = t_clean

        # Normalize IPv6 loopback
        if "::1" in t_clean:
            if active_dev_ports:
                normalized_url = f"http://[::1]:{active_dev_ports[0]}"
            else:
                normalized_url = "http://[::1]"
        # Normalize localhost / 127.0.0.1 without explicit port
        elif any(x in t_clean for x in ["localhost", "127.0.0.1", "0.0.0.0"]):
            if len(active_dev_ports) == 1:
                normalized_url = f"http://localhost:{active_dev_ports[0]}"
            elif active_dev_ports:
                normalized_url = f"http://localhost:{active_dev_ports[0]}"
            else:
                normalized_url = "http://localhost"

        elif not t_clean.startswith(("http://", "https://", "ftp://")):
            if t_clean.startswith("localhost") or t_clean.startswith("127.0.0.1") or re.match(r"^\d{1,3}\.", t_clean):
                normalized_url = f"http://{t_clean}"
            else:
                normalized_url = f"https://{t_clean}"

        return {
            "resource_type": ResourceType.URL,
            "confidence": confidence,
            "resolved_target": normalized_url,
            "action": "open_url",
            "metadata": {
                "active_dev_ports": active_dev_ports,
                "browser": target_browser,
                "original_input": target
            }
        }

    def _scan_active_dev_ports(self) -> list[int]:
        """Scan active TCP listening sockets for web dev server ports."""
        active_ports = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    port = conn.laddr.port
                    if port in self.COMMON_DEV_PORTS and port not in active_ports:
                        active_ports.append(port)
        except Exception:
            pass
        return sorted(active_ports)
