"""Newsletter and Subscription Hygiene Engine.

NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""

from __future__ import annotations

import re
from collections import defaultdict

from inboxguard.models import EmailMessage, EmailTier, SenderProfile, UnsubscribeMechanism


class NewsletterCleaner:
    """Extracts subscription mechanisms, tracks open/read engagement, and calculates subscription decay."""

    @staticmethod
    def parse_unsubscribe_header(header_val: str, post_val: str = "") -> tuple[UnsubscribeMechanism, str, str]:
        """Parse RFC 2369 and RFC 8058 List-Unsubscribe headers."""
        if not header_val:
            return UnsubscribeMechanism.NONE, "", ""

        url_match = re.search(r"<(https?://[^>]+)>", header_val)
        mailto_match = re.search(r"<(mailto:[^>]+)>", header_val)

        url = url_match.group(1) if url_match else ""
        mailto = mailto_match.group(1) if mailto_match else ""

        if post_val and "list-unsubscribe=one-click" in post_val.lower() and url:
            return UnsubscribeMechanism.ONE_CLICK, url, mailto
        if url:
            return UnsubscribeMechanism.HTTPS_LINK, url, mailto
        if mailto:
            return UnsubscribeMechanism.MAILTO, "", mailto

        return UnsubscribeMechanism.NONE, "", ""

    def analyze_senders(self, messages: list[EmailMessage]) -> list[SenderProfile]:
        """Aggregate messages by sender, identify subscriptions, and calculate decay scores."""
        senders_map: dict[str, list[EmailMessage]] = defaultdict(list)
        for msg in messages:
            senders_map[msg.sender_email.lower()].append(msg)

        profiles: list[SenderProfile] = []

        for email, msgs in senders_map.items():
            total = len(msgs)
            unread = sum(1 for m in msgs if not m.is_read)
            read_rate = (total - unread) / total if total > 0 else 0.0

            # Find dominant tier
            tier_counts: dict[EmailTier, int] = defaultdict(int)
            for m in msgs:
                tier_counts[m.tier] += 1
            dominant_tier = (
                max(tier_counts.keys(), key=lambda k: tier_counts[k]) if tier_counts else EmailTier.TIER_4_SUBSCRIPTIONS
            )

            # Check if any email had unsubscribe info
            unsub_url = ""
            unsub_mailto = ""
            is_sub = False
            for m in msgs:
                if m.unsubscribe_url:
                    unsub_url = m.unsubscribe_url
                    is_sub = True
                if m.unsubscribe_mailto:
                    unsub_mailto = m.unsubscribe_mailto
                    is_sub = True
                if m.tier == EmailTier.TIER_4_SUBSCRIPTIONS:
                    is_sub = True

            dates = sorted([m.date for m in msgs if m.date])
            first_seen = dates[0] if dates else ""
            last_seen = dates[-1] if dates else ""

            # Calculate decay score (0.0 to 1.0)
            # High decay = high unread count, low read rate, frequent volume
            decay_score = 0.0
            if is_sub or dominant_tier in [EmailTier.TIER_4_SUBSCRIPTIONS, EmailTier.TIER_5_COLD_PROMO_SPAM]:
                unread_ratio = unread / total if total > 0 else 1.0
                volume_weight = min(1.0, total / 10.0)
                decay_score = round(unread_ratio * 0.7 + volume_weight * 0.3, 3)

            name = msgs[0].sender_name or email
            profile = SenderProfile(
                sender_email=email,
                sender_name=name,
                total_count=total,
                unread_count=unread,
                read_rate=round(read_rate, 3),
                dominant_tier=dominant_tier,
                first_seen=first_seen,
                last_seen=last_seen,
                unsubscribe_url=unsub_url,
                unsubscribe_mailto=unsub_mailto,
                is_subscription=is_sub,
                decay_score=decay_score,
            )
            profiles.append(profile)

        # Sort profiles by decay score descending, then unread count descending
        profiles.sort(key=lambda p: (p.decay_score, p.unread_count, p.total_count), reverse=True)
        return profiles

    def extract_decayed_subscriptions(
        self, profiles: list[SenderProfile], threshold: float = 0.5
    ) -> list[SenderProfile]:
        """Filter senders that represent abandoned or decayed subscriptions."""
        return [
            p
            for p in profiles
            if (p.is_subscription or p.dominant_tier == EmailTier.TIER_4_SUBSCRIPTIONS) and p.decay_score >= threshold
        ]
