# NOTE: This project is for Proof of Concept (POC) purposes only. It is not intended for production use.
"""
Core estate planning engine: Funding audit, probate risk scoring, and beneficiary distribution waterfalls.
"""

from .models import (
    BeneficiaryPayout,
    DistributionScheme,
    FundingAuditReport,
    TitlingStatus,
    TrustEntity,
    WaterfallResult,
)


class EstateEngine:
    """Computes estate funding ratios, probate exposure, and beneficiary distribution waterfalls."""

    @staticmethod
    def audit_funding(trust: TrustEntity) -> FundingAuditReport:
        """Scan trust Schedule A assets for unfunded assets that risk probate court exposure."""
        total = trust.total_estate_value
        if total <= 0:
            return FundingAuditReport(
                total_estate_value=0.0,
                funded_to_trust_value=0.0,
                funded_to_trust_pct=100.0,
                beneficiary_designated_value=0.0,
                unfunded_probate_risk_value=0.0,
                unfunded_probate_risk_pct=0.0,
                at_risk_assets=[],
                probate_risk_tier="Zero Estate Value",
            )

        funded_val = sum(
            a.estimated_value
            for a in trust.assets
            if a.titling_status == TitlingStatus.TITLED_TO_TRUST
            or a.titling_status == TitlingStatus.TITLED_TO_TRUST.value
        )
        desig_val = sum(
            a.estimated_value
            for a in trust.assets
            if a.titling_status == TitlingStatus.BENEFICIARY_DESIGNATED
            or a.titling_status == TitlingStatus.BENEFICIARY_DESIGNATED.value
        )
        unfunded_assets = [
            a
            for a in trust.assets
            if a.titling_status
            in [
                TitlingStatus.UNFUNDED_PROBATE_RISK,
                TitlingStatus.UNFUNDED_PROBATE_RISK.value,
                TitlingStatus.POUR_OVER_WILL_ONLY,
                TitlingStatus.POUR_OVER_WILL_ONLY.value,
            ]
        ]
        unfunded_val = sum(a.estimated_value for a in unfunded_assets)

        unfunded_pct = (unfunded_val / total) * 100.0
        funded_pct = (funded_val / total) * 100.0

        if unfunded_pct == 0:
            tier = "Optimal (100% Trust Funded / Designated - Zero Probate Spillover)"
        elif unfunded_pct < 15:
            tier = "Low (Minor Unfunded Personal Property / Under Statutory Limits)"
        elif unfunded_pct <= 40:
            tier = "Moderate (Substantial Assets Require Pour-Over Will & Ancillary Probate)"
        else:
            tier = "Critical (Major Titling Deficiency - High Probate Court Risk & Delay)"

        return FundingAuditReport(
            total_estate_value=round(total, 2),
            funded_to_trust_value=round(funded_val, 2),
            funded_to_trust_pct=round(funded_pct, 1),
            beneficiary_designated_value=round(desig_val, 2),
            unfunded_probate_risk_value=round(unfunded_val, 2),
            unfunded_probate_risk_pct=round(unfunded_pct, 1),
            at_risk_assets=unfunded_assets,
            probate_risk_tier=tier,
        )

    @staticmethod
    def calculate_waterfall(
        trust: TrustEntity,
        gross_estate_override: float | None = None,
        administrative_reserve_pct: float = 3.0,
    ) -> WaterfallResult:
        """Simulate estate distribution waterfall across specific bequests and percentage beneficiaries."""
        gross = gross_estate_override if gross_estate_override is not None else trust.total_estate_value
        admin_dollars = gross * (administrative_reserve_pct / 100.0)
        net_distributable = max(0.0, gross - admin_dollars)

        primary_bens = [b for b in trust.beneficiaries if b.is_primary]
        if not primary_bens:
            return WaterfallResult(
                gross_estate_value=round(gross, 2),
                administrative_reserve_pct=administrative_reserve_pct,
                administrative_reserve_dollars=round(admin_dollars, 2),
                distributable_net_estate=round(net_distributable, 2),
                payouts=[],
                unallocated_remainder=round(net_distributable, 2),
            )

        # Step 1: Specific dollar bequests
        dollar_allocated = 0.0
        payouts: list[BeneficiaryPayout] = []
        percentage_bens = []

        for b in primary_bens:
            if (
                b.scheme == DistributionScheme.SPECIFIC_DOLLAR_BEQUEST
                or b.scheme == DistributionScheme.SPECIFIC_DOLLAR_BEQUEST.value
            ):
                amt = min(b.specific_dollar_amount, max(0.0, net_distributable - dollar_allocated))
                dollar_allocated += amt
                payouts.append(
                    BeneficiaryPayout(
                        beneficiary_name=b.beneficiary_name,
                        allocation_pct=round((amt / net_distributable * 100.0) if net_distributable > 0 else 0.0, 1),
                        total_dollar_amount=round(amt, 2),
                        immediate_payout=round(amt, 2),
                    )
                )
            else:
                percentage_bens.append(b)

        # Step 2: Residual percentage distribution
        residual_estate = max(0.0, net_distributable - dollar_allocated)
        total_pct = sum(b.share_pct for b in percentage_bens)
        allocated_pct_dollars = 0.0

        for b in percentage_bens:
            # Normalize percentage if not totaling 100%
            effective_share = (b.share_pct / total_pct) if total_pct > 0 else 0.0
            beneficiary_total = residual_estate * effective_share
            allocated_pct_dollars += beneficiary_total

            # Check age milestones
            milestones = []
            immediate = beneficiary_total
            if (
                b.scheme in [DistributionScheme.AGE_MILESTONE_TRANCHES, DistributionScheme.AGE_MILESTONE_TRANCHES.value]
                and b.milestone_schedule
            ):
                immediate = 0.0
                for ms in b.milestone_schedule:
                    age = ms.get("age", 30)
                    frac = ms.get("fraction", 1.0)
                    chunk_val = beneficiary_total * frac
                    milestones.append(
                        {
                            "release_age": age,
                            "fraction_pct": round(frac * 100.0, 1),
                            "estimated_amount": round(chunk_val, 2),
                        }
                    )

            payouts.append(
                BeneficiaryPayout(
                    beneficiary_name=b.beneficiary_name,
                    allocation_pct=round(b.share_pct, 1),
                    total_dollar_amount=round(beneficiary_total, 2),
                    immediate_payout=round(immediate, 2),
                    milestone_tranches=milestones,
                )
            )

        unallocated = max(0.0, net_distributable - (dollar_allocated + allocated_pct_dollars))

        return WaterfallResult(
            gross_estate_value=round(gross, 2),
            administrative_reserve_pct=administrative_reserve_pct,
            administrative_reserve_dollars=round(admin_dollars, 2),
            distributable_net_estate=round(net_distributable, 2),
            payouts=payouts,
            unallocated_remainder=round(unallocated, 2),
        )
