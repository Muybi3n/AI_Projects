# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""CanaryMesh integrity tripwire engine: monitors decoys, computes cryptographic drift, detects tampering."""

from __future__ import annotations

from pathlib import Path

from canarymesh.generator import compute_file_hashes
from canarymesh.models import (
    AlertSeverity,
    DecoyArtifact,
    DecoyAuditSummary,
    TripwireAlert,
    TripwireTriggerType,
    utc_now_iso,
)


class TripwireEngine:
    """Evaluates decoy filesystem integrity and generates actionable alerts on anomaly or breach."""

    def __init__(self, check_atime: bool = False, atime_threshold_seconds: int = 3600):
        self.check_atime = check_atime
        self.atime_threshold_seconds = atime_threshold_seconds

    def check_artifact(self, artifact: DecoyArtifact) -> tuple[bool, list[TripwireAlert]]:
        """Audits a single decoy artifact against its baseline cryptographic state.

        Returns (is_intact, list_of_alerts).
        """
        alerts: list[TripwireAlert] = []
        path = Path(artifact.file_path)

        # 1. Existence check
        if not path.exists():
            alert = TripwireAlert(
                alert_id=f"ALT-{artifact.token_id[:8]}-MISSING",
                token_id=artifact.token_id,
                file_path=str(path),
                trigger_type=TripwireTriggerType.MISSING,
                severity=AlertSeverity.CRITICAL,
                detected_at=utc_now_iso(),
                mitre_technique="T1070.004 - Indicator Removal on Host: File Deletion",
                summary=f"CRITICAL: Canary decoy file missing or deleted: {path.name}",
                details={
                    "expected_path": str(path),
                    "canary_identifier": artifact.canary_identifier,
                    "category": artifact.category.value,
                },
            )
            alerts.append(alert)
            return False, alerts

        # 2. Cryptographic Hash & Tampering Check
        try:
            curr_sha, curr_blake, curr_size = compute_file_hashes(path)
        except (OSError, PermissionError) as e:
            alert = TripwireAlert(
                alert_id=f"ALT-{artifact.token_id[:8]}-PERM",
                token_id=artifact.token_id,
                file_path=str(path),
                trigger_type=TripwireTriggerType.PERMISSION_CHANGED,
                severity=AlertSeverity.HIGH,
                detected_at=utc_now_iso(),
                mitre_technique="T1222 - File and Directory Permissions Modification",
                summary=f"HIGH: Cannot read canary file (permission denied or locked): {path.name}",
                details={"error": str(e)},
            )
            alerts.append(alert)
            return False, alerts

        if curr_sha != artifact.expected_sha256 or curr_blake != artifact.expected_blake2b:
            alert = TripwireAlert(
                alert_id=f"ALT-{artifact.token_id[:8]}-TAMPER",
                token_id=artifact.token_id,
                file_path=str(path),
                trigger_type=TripwireTriggerType.TAMPERED,
                severity=AlertSeverity.CRITICAL,
                detected_at=utc_now_iso(),
                mitre_technique="T1565.001 - Data Manipulation: Stored Data Manipulation",
                summary=f"CRITICAL BREACH ALERT: Decoy file cryptographic signature changed! ({path.name})",
                details={
                    "expected_sha256": artifact.expected_sha256,
                    "actual_sha256": curr_sha,
                    "expected_size_bytes": artifact.file_size_bytes,
                    "actual_size_bytes": curr_size,
                    "canary_identifier": artifact.canary_identifier,
                },
            )
            alerts.append(alert)
            return False, alerts

        # 3. Access Time (atime) check if enabled
        if self.check_atime:
            try:
                stat_info = path.stat()
                atime = stat_info.st_atime
                mtime = stat_info.st_mtime
                # If file was read significantly after creation/modification
                if atime > mtime + 5:
                    alert = TripwireAlert(
                        alert_id=f"ALT-{artifact.token_id[:8]}-ACCESS",
                        token_id=artifact.token_id,
                        file_path=str(path),
                        trigger_type=TripwireTriggerType.ACCESSED_ATIME,
                        severity=AlertSeverity.MEDIUM,
                        detected_at=utc_now_iso(),
                        mitre_technique="T1005 - Data from Local System",
                        summary=f"MEDIUM: Decoy file read access detected via st_atime: {path.name}",
                        details={
                            "st_atime": atime,
                            "st_mtime": mtime,
                            "canary_identifier": artifact.canary_identifier,
                        },
                    )
                    alerts.append(alert)
                    # Note: file contents are still intact, but reading is an indicator
                    return True, alerts
            except OSError:
                pass

        return True, []

    def run_fleet_audit(self, artifacts: list[DecoyArtifact]) -> DecoyAuditSummary:
        """Audits all active registered decoy artifacts and compiles an audit summary."""
        total = len(artifacts)
        active_list = [art for art in artifacts if art.is_active]
        active_count = len(active_list)

        intact_count = 0
        tampered_count = 0
        missing_count = 0
        fleet_alerts: list[TripwireAlert] = []

        now_str = utc_now_iso()

        for art in active_list:
            is_intact, alerts = self.check_artifact(art)
            art.last_checked_at = now_str
            if alerts:
                fleet_alerts.extend(alerts)
                for a in alerts:
                    if a.trigger_type in (TripwireTriggerType.MISSING, TripwireTriggerType.DELETED):
                        missing_count += 1
                    elif a.trigger_type == TripwireTriggerType.TAMPERED:
                        tampered_count += 1
            if is_intact:
                intact_count += 1

        if tampered_count > 0 or missing_count > 0:
            health = "BREACH_OR_TAMPER_DETECTED"
        elif fleet_alerts:
            health = "WARNING_SUSPICIOUS_ACTIVITY"
        else:
            health = "ALL_DECOYS_INTACT"

        return DecoyAuditSummary(
            timestamp=now_str,
            total_decoys=total,
            active_decoys=active_count,
            intact_decoys=intact_count,
            tampered_decoys=tampered_count,
            missing_decoys=missing_count,
            alerts_generated=len(fleet_alerts),
            overall_health=health,
            alerts=fleet_alerts,
        )

    @staticmethod
    def simulate_token_alert(
        artifact: DecoyArtifact, source_ip: str = "198.51.100.42", user_agent: str = "curl/7.88.1"
    ) -> TripwireAlert:
        """Simulates an external honeynet hit or API token detonation alert."""
        return TripwireAlert(
            alert_id=f"ALT-{artifact.token_id[:8]}-TOKEN-DETONATE",
            token_id=artifact.token_id,
            file_path=artifact.file_path,
            trigger_type=TripwireTriggerType.TOKEN_PING,
            severity=AlertSeverity.CRITICAL,
            detected_at=utc_now_iso(),
            mitre_technique="T1078 - Valid Accounts",
            summary=f"CRITICAL: Canary honey-token used by external actor! ({artifact.name})",
            details={
                "source_ip": source_ip,
                "user_agent": user_agent,
                "canary_identifier": artifact.canary_identifier,
                "category": artifact.category.value,
            },
        )
