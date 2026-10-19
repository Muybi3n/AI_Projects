# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh generator: Synthesizes realistic defensive decoy honey-tokens and canary artifacts."""

from __future__ import annotations

import hashlib
import os
import secrets
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from canarymesh.models import DecoyCategory


@dataclass
class DecoyTemplate:
    category: DecoyCategory
    filename: str
    default_technique: str
    description: str


DECOY_TEMPLATES: dict[DecoyCategory, DecoyTemplate] = {
    DecoyCategory.AWS_CREDENTIALS: DecoyTemplate(
        category=DecoyCategory.AWS_CREDENTIALS,
        filename="credentials",
        default_technique="T1552.001 - Credentials In Files",
        description="Defensive AWS credential honey-token with deterministic canary key ID",
    ),
    DecoyCategory.SSH_KEY: DecoyTemplate(
        category=DecoyCategory.SSH_KEY,
        filename="id_rsa_backup",
        default_technique="T1552.004 - Private Keys",
        description="Encrypted decoy OpenSSH private key header with canary signature marker",
    ),
    DecoyCategory.ENV_SECRETS: DecoyTemplate(
        category=DecoyCategory.ENV_SECRETS,
        filename=".env.production",
        default_technique="T1552.001 - Credentials In Files",
        description="Decoy staging/production environment variable configuration with fake service tokens",
    ),
    DecoyCategory.DATABASE_CONFIG: DecoyTemplate(
        category=DecoyCategory.DATABASE_CONFIG,
        filename="database.yml",
        default_technique="T1552.001 - Credentials In Files",
        description="Decoy database connection configuration pointing to honeynet listeners",
    ),
    DecoyCategory.API_TOKEN: DecoyTemplate(
        category=DecoyCategory.API_TOKEN,
        filename="api_keys.json",
        default_technique="T1552.001 - Credentials In Files",
        description="Decoy API token bundle formatted for Stripe, GitHub, or OpenAI honey-tokens",
    ),
    DecoyCategory.SENSITIVE_DOCUMENT: DecoyTemplate(
        category=DecoyCategory.SENSITIVE_DOCUMENT,
        filename="confidential_q4_acquisition.md",
        default_technique="T1083 - File and Directory Discovery",
        description="Executive canary document bait with embedded tracking UUID markers",
    ),
    DecoyCategory.CUSTOM: DecoyTemplate(
        category=DecoyCategory.CUSTOM,
        filename="decoy_canary.txt",
        default_technique="T1078 - Valid Accounts",
        description="Custom decoy honeypot tripwire artifact",
    ),
}


def generate_canary_identifier(prefix: str = "CANARY") -> str:
    """Generate an unguessable 16-character cryptographic hex token marker."""
    entropy = secrets.token_hex(8)
    return f"{prefix}-{entropy.upper()}"


def _generate_random_secret(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def build_decoy_payload(
    category: DecoyCategory,
    canary_id: str,
    custom_label: str = "defensive-tripwire",
) -> tuple[str, dict[str, Any]]:
    """Synthesizes high-fidelity decoy file content incorporating the canary identifier."""
    meta: dict[str, Any] = {"canary_id": canary_id, "label": custom_label}

    if category == DecoyCategory.AWS_CREDENTIALS:
        access_key = f"AKIA{canary_id.replace('-', '')[:16]}"
        secret_key = _generate_random_secret(40)
        content = (
            "# DO NOT EDIT - Production Backup Access Credentials\n"
            "[default]\n"
            f"aws_access_key_id = {access_key}\n"
            f"aws_secret_access_key = {secret_key}\n"
            "region = us-east-1\n"
            f"# Canary Reference: {canary_id}\n"
        )
        meta["access_key_prefix"] = access_key[:8]

    elif category == DecoyCategory.SSH_KEY:
        header = "-----BEGIN OPENSSH PRIVATE KEY-----"
        footer = "-----END OPENSSH PRIVATE KEY-----"
        # Synthetic base64 body chunks containing the marker in comment
        body_chunk_1 = "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAABlwAAAAdzc2gtcn"
        body_chunk_2 = f"NhAAAAAwEAAQAAAYEAmQ{canary_id.replace('-', '')}K9xO7vP"
        body_chunk_3 = "8w4r5Xy9z1A2b3C4d5E6f7G8h9I0j1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7"
        body_chunk_4 = "8w4r5Xy9z1A2b3C4d5E6f7G8h9I0j1K2L3M4N5O6P7Q8R9S0T1U2V3W4X5Y6Z7AAAA"
        content = f"{header}\n{body_chunk_1}\n{body_chunk_2}\n{body_chunk_3}\n{body_chunk_4}\n{footer}\n"
        meta["key_type"] = "RSA-3072"

    elif category == DecoyCategory.ENV_SECRETS:
        content = (
            "# Internal Production API Secrets & Microservice Environment\n"
            f"CANARY_TRACKER_ID={canary_id}\n"
            f"DATABASE_URL=postgres://app_svc_readonly:pw_{canary_id}@10.0.99.254:5432/corp_prod\n"
            f"STRIPE_API_KEY=sk_live_canary_{_generate_random_secret(24)}\n"
            f"GITHUB_ENTERPRISE_TOKEN=ghp_canary{_generate_random_secret(30)}\n"
            "ENVIRONMENT=production\n"
            "LOG_LEVEL=info\n"
        )

    elif category == DecoyCategory.DATABASE_CONFIG:
        content = (
            "production:\n"
            "  adapter: postgresql\n"
            "  encoding: unicode\n"
            "  database: internal_analytics_prod\n"
            "  pool: 10\n"
            "  username: analytics_canary_user\n"
            f"  password: db_sec_{canary_id}\n"
            "  host: db-audit-honeynet.corp.local\n"
            "  port: 5432\n"
        )

    elif category == DecoyCategory.API_TOKEN:
        content = (
            "{\n"
            f'  "_comment": "Internal service credentials - Canary ID {canary_id}",\n'
            f'  "stripe_secret": "sk_live_{_generate_random_secret(28)}",\n'
            f'  "slack_bot_token": "xoxb-{canary_id}-mockslacktoken",\n'
            '  "openai_api_key": "sk-proj-canary-mock-not-real-token-0123456789",\n'
            '  "environment": "restricted-vault"\n'
            "}\n"
        )

    elif category == DecoyCategory.SENSITIVE_DOCUMENT:
        content = (
            "# CONFIDENTIAL - ACQUISITION ASSESSMENT & FINANCIAL DUE DILIGENCE\n\n"
            f"> Internal Reference Audit ID: `{canary_id}`\n\n"
            "## Executive Summary\n"
            "This document summarizes high-level acquisition targets and valuation models for FY2026.\n"
            "Distribution is strictly limited to M&A Committee members.\n\n"
            "## Target Portfolio Metrics\n"
            "- Target Entity: Project Echo Ltd.\n"
            "- Enterprise Valuation: $42,500,000 USD\n"
            "- Core Assets: Proprietary autonomous inference pipelines & IP patents.\n\n"
            f"<!-- CANARY_WATERMARK: {canary_id} -->\n"
        )

    else:  # CUSTOM
        content = (
            f"CANARYMESH_HONEY_TOKEN={canary_id}\n"
            f"CREATED_FOR={custom_label}\n"
            "STATUS=TRIPWIRE_ARMED\n"
            "NOTICE=Access to this resource is monitored and logged.\n"
        )

    return content, meta


def compute_file_hashes(path_or_bytes: Path | bytes) -> tuple[str, str, int]:
    """Compute SHA-256 and BLAKE2b hashes and byte length."""
    if isinstance(path_or_bytes, (str, Path)):
        p = Path(path_or_bytes)
        data = p.read_bytes()
    else:
        data = path_or_bytes

    sha256_hash = hashlib.sha256(data).hexdigest()
    blake2b_hash = hashlib.blake2b(data).hexdigest()
    return sha256_hash, blake2b_hash, len(data)


def deploy_decoy_file(
    target_path: Path,
    category: DecoyCategory,
    canary_id: str,
    custom_label: str = "defensive-tripwire",
) -> tuple[str, str, int, dict[str, Any]]:
    """Generates and writes a decoy file to disk, returning hashes and metadata."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    content, meta = build_decoy_payload(category, canary_id, custom_label)

    target_path.write_text(content, encoding="utf-8")
    # Restrict permissions to standard owner rw (0o600) for credentials
    if category in (DecoyCategory.AWS_CREDENTIALS, DecoyCategory.SSH_KEY, DecoyCategory.ENV_SECRETS):
        os.chmod(target_path, 0o600)

    sha256_hash, blake2b_hash, size = compute_file_hashes(target_path)
    return sha256_hash, blake2b_hash, size, meta
