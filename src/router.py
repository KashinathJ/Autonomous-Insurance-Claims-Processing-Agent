"""
Routing logic for FNOL claims.
Evaluates extracted data against mandatory rules and returns recommended route + reasoning.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from .schema import FNOLDocument

# Keywords that trigger investigation flag (case-insensitive)
INVESTIGATION_KEYWORDS = ("fraud", "inconsistent", "staged")

# Threshold for fast-track (currency-agnostic numeric comparison)
FAST_TRACK_DAMAGE_THRESHOLD = 25_000.0


@dataclass
class RoutingDecision:
    """Result of routing evaluation."""

    recommended_route: str  # e.g. "fast_track", "manual_review", "investigation", "specialist"
    reasoning: List[str]
    flags: List[str]  # e.g. "missing_policy_number", "injury_claim"
    is_decision_ready: bool  # True if no blocking issues for auto-routing


def _has_mandatory_fields(doc: FNOLDocument) -> Tuple[bool, List[str]]:
    """
    Check mandatory fields: Policy #, (Holder) Name, Incident Date.
    Returns (all_present, list of missing field descriptions).
    """
    missing: List[str] = []
    if not doc.policy or not (doc.policy.number and str(doc.policy.number).strip()):
        missing.append("Policy number")
    name = None
    if doc.parties and doc.parties.claimant and doc.parties.claimant.name:
        name = doc.parties.claimant.name
    if not name and doc.policy and doc.policy.holder_name:
        name = doc.policy.holder_name
    if not name or not str(name).strip():
        missing.append("Policy holder / claimant name")
    incident_date = None
    if doc.incident and doc.incident.date:
        incident_date = doc.incident.date
    if not incident_date:
        missing.append("Incident date")
    return (len(missing) == 0, missing)


def _get_estimated_damage(doc: FNOLDocument) -> Optional[float]:
    """Return estimated damage amount from asset or status."""
    if doc.asset and doc.asset.estimated_damage is not None:
        return float(doc.asset.estimated_damage)
    if doc.status and doc.status.initial_estimate is not None:
        return float(doc.status.initial_estimate)
    return None


def _description_contains_keywords(doc: FNOLDocument) -> bool:
    """True if incident description contains any of INVESTIGATION_KEYWORDS."""
    desc = None
    if doc.incident and doc.incident.description:
        desc = doc.incident.description
    if not desc:
        return False
    lower = desc.lower()
    return any(kw in lower for kw in INVESTIGATION_KEYWORDS)


def _is_injury_claim(doc: FNOLDocument) -> bool:
    """True if claim type is injury (case-insensitive)."""
    if not doc.status or not doc.status.claim_type:
        return False
    return doc.status.claim_type.strip().lower() == "injury"


def route_fnol(doc: FNOLDocument) -> RoutingDecision:
    """
    Evaluate the extracted FNOL document against the 4 mandatory routing rules.
    Returns a single recommended route with reasoning and flags.
    Priority order: Manual Review (missing mandatory) > Investigation > Specialist > Fast-track.
    """
    reasoning: List[str] = []
    flags: List[str] = []

    # 1) Mandatory fields -> Manual Review
    has_mandatory, missing = _has_mandatory_fields(doc)
    if not has_mandatory:
        flags.append("missing_mandatory_fields")
        reasoning.append(f"Mandatory fields missing: {', '.join(missing)}. Requires manual review.")
        return RoutingDecision(
            recommended_route="manual_review",
            reasoning=reasoning,
            flags=flags,
            is_decision_ready=False,
        )

    # 2) Investigation keywords in description
    if _description_contains_keywords(doc):
        flags.append("investigation_keywords")
        reasoning.append(
            "Incident description contains one or more of: 'fraud', 'inconsistent', 'staged'. Flagged for investigation."
        )
        return RoutingDecision(
            recommended_route="investigation",
            reasoning=reasoning,
            flags=flags,
            is_decision_ready=False,
        )

    # 3) Injury claim -> Specialist Queue
    if _is_injury_claim(doc):
        flags.append("injury_claim")
        reasoning.append("Claim type is 'injury'. Route to specialist queue.")
        return RoutingDecision(
            recommended_route="specialist",
            reasoning=reasoning,
            flags=flags,
            is_decision_ready=True,
        )

    # 4) Estimated damage < 25,000 -> Fast-track
    damage = _get_estimated_damage(doc)
    if damage is not None and damage < FAST_TRACK_DAMAGE_THRESHOLD:
        reasoning.append(
            f"Estimated damage ({damage}) is below {FAST_TRACK_DAMAGE_THRESHOLD}. Fast-track eligible."
        )
        return RoutingDecision(
            recommended_route="fast_track",
            reasoning=reasoning,
            flags=flags,
            is_decision_ready=True,
        )

    # Default: standard queue (no fast-track, no specialist, no investigation)
    reasoning.append(
        "No special routing conditions met. Standard processing queue."
    )
    if damage is not None:
        reasoning.append(f"Estimated damage: {damage} (not below fast-track threshold).")
    return RoutingDecision(
        recommended_route="standard",
        reasoning=reasoning,
        flags=flags,
        is_decision_ready=True,
    )
