"""Local HTTP reverse-proxy handling OpenAI / Ollama compatible chat completion payloads.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

import json
import logging
import socket
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

from promptguard.detector import InjectionDetector
from promptguard.models import ActionVerdict, AuditLogEntry, ProxyConfig
from promptguard.storage import AuditStorage

logger = logging.getLogger("promptguard.proxy")


def create_proxy_handler(config: ProxyConfig, storage: AuditStorage, detector: InjectionDetector):
    """Factory creating an HTTP handler bound to config and detector instances."""

    class PromptGuardHTTPHandler(BaseHTTPRequestHandler):
        def log_message(self, format_str: str, *args) -> None:
            # Suppress default noisy stderr web logs during CLI operations
            pass

        def do_GET(self) -> None:
            """Health and proxy status endpoint."""
            if self.path in ("/health", "/v1/health"):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                stats = storage.get_summary_stats()
                body = {
                    "status": "healthy",
                    "mode": "reverse_proxy",
                    "block_threshold": config.block_threshold,
                    "stats": stats,
                }
                self.wfile.write(json.dumps(body).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self) -> None:
            """Intercepts, scans, sanitizes, or blocks LLM prompts before forwarding."""
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length)

            req_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now(timezone.utc).isoformat()
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"

            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON payload"}).encode("utf-8"))
                return

            # Extract user prompts from standard OpenAI / Ollama payload format
            # e.g., payload = {"messages": [{"role": "user", "content": "..."}], ...}
            # or payload = {"prompt": "..."}
            prompts_to_scan: list[str] = []
            if "messages" in payload and isinstance(payload["messages"], list):
                for msg in payload["messages"]:
                    if isinstance(msg, dict) and "content" in msg and isinstance(msg["content"], str):
                        prompts_to_scan.append(msg["content"])
            elif "prompt" in payload and isinstance(payload["prompt"], str):
                prompts_to_scan.append(payload["prompt"])

            combined_prompt = "\n".join(prompts_to_scan)
            scan_result = detector.evaluate(combined_prompt)

            # Record audit entry
            audit_entry = AuditLogEntry(
                request_id=req_id,
                timestamp=timestamp,
                client_ip=client_ip,
                upstream_url=config.upstream_url,
                verdict=scan_result.verdict,
                risk_tier=scan_result.risk_tier,
                risk_score=scan_result.risk_score,
                pii_count=len(scan_result.pii_matches),
                threat_count=len(scan_result.threats),
                reasons=scan_result.reasons,
                sanitized_preview=scan_result.sanitized_text[:120],
            )
            storage.append(audit_entry)

            # Action: BLOCK
            if scan_result.verdict == ActionVerdict.BLOCK:
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                block_response = {
                    "error": {
                        "message": "Request blocked by PromptGuard security policy (Prompt Injection detected)",
                        "type": "prompt_injection_violation",
                        "request_id": req_id,
                        "risk_score": scan_result.risk_score,
                        "risk_tier": scan_result.risk_tier.value,
                        "threats": [t.to_dict() for t in scan_result.threats],
                        "reasons": scan_result.reasons,
                    }
                }
                self.wfile.write(json.dumps(block_response).encode("utf-8"))
                return

            # Action: SANITIZE (replace payload contents with sanitized tokens)
            if scan_result.verdict == ActionVerdict.SANITIZE_AND_FORWARD:
                if "messages" in payload and isinstance(payload["messages"], list):
                    for msg in payload["messages"]:
                        if isinstance(msg, dict) and "content" in msg and isinstance(msg["content"], str):
                            sanitized, _ = detector.sanitizer.sanitize(msg["content"])
                            msg["content"] = sanitized
                elif "prompt" in payload and isinstance(payload["prompt"], str):
                    sanitized, _ = detector.sanitizer.sanitize(payload["prompt"])
                    payload["prompt"] = sanitized

            # Forward to upstream LLM service
            forwarded_body = json.dumps(payload).encode("utf-8")
            target_url = f"{config.upstream_url.rstrip('/')}{self.path}"

            headers = {
                "Content-Type": "application/json",
                "X-PromptGuard-ID": req_id,
                "X-PromptGuard-RiskScore": str(scan_result.risk_score),
            }
            # Propagate authorization if present
            if "Authorization" in self.headers:
                headers["Authorization"] = self.headers["Authorization"]

            req = urllib.request.Request(target_url, data=forwarded_body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp_status = resp.status
                    resp_body = resp.read()
                    resp_headers = resp.headers

                    self.send_response(resp_status)
                    for k, v in resp_headers.items():
                        if k.lower() not in ("transfer-encoding", "content-length"):
                            self.send_header(k, v)
                    self.send_header("Content-Length", str(len(resp_body)))
                    self.send_header("X-PromptGuard-Verdict", scan_result.verdict.value)
                    self.end_headers()
                    self.wfile.write(resp_body)
            except urllib.error.HTTPError as e:
                self.send_response(e.code)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(e.read())
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                self.send_response(502)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                err_resp = {
                    "error": {
                        "message": f"PromptGuard could not connect to upstream LLM ({config.upstream_url}): {e}",
                        "type": "bad_gateway",
                        "request_id": req_id,
                    }
                }
                self.wfile.write(json.dumps(err_resp).encode("utf-8"))

    return PromptGuardHTTPHandler


def run_proxy(config: ProxyConfig, storage: AuditStorage, detector: InjectionDetector) -> HTTPServer:
    """Instantiates and starts the local HTTPServer."""
    handler_cls = create_proxy_handler(config, storage, detector)
    server = HTTPServer((config.listen_host, config.listen_port), handler_cls)
    return server


def find_free_port(host: str = "127.0.0.1") -> int:
    """Finds an unused port on the given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]
