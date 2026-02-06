"""
Output format and missing-fields logic for FNOL.
Builds extractedFields, missingFields, recommendedRoute, reasoning per spec.
"""

from typing import Any, List

from .schema import FNOLDocument
from .router import RoutingDecision, route_fnol


# All extractable fields (label -> path to value). Used for form display and missingFields.
CLAIM_FIELD_SPEC = [
    # Policy Information
    ("Policy Number", lambda d: d.policy and d.policy.number),
    ("Policyholder Name", lambda d: d.policy and d.policy.holder_name),
    ("Effective Date Start", lambda d: d.policy and d.policy.effective_date_start),
    ("Effective Date End", lambda d: d.policy and d.policy.effective_date_end),
    # Incident Information
    ("Incident Date", lambda d: d.incident and d.incident.date),
    ("Incident Time", lambda d: d.incident and d.incident.time),
    ("Location", lambda d: d.incident and d.incident.location),
    ("Description", lambda d: d.incident and d.incident.description),
    # Involved Parties
    ("Claimant", lambda d: (d.parties and d.parties.claimant and d.parties.claimant.name) or None),
    ("Third Parties", lambda d: (d.parties and d.parties.third_parties) and [p.name for p in d.parties.third_parties if p and p.name] or None),
    ("Contact Phone", lambda d: (d.parties and d.parties.contact_details and d.parties.contact_details.phone)
        or (d.parties and d.parties.claimant and d.parties.claimant.contact and d.parties.claimant.contact.phone)),
    ("Contact Email", lambda d: (d.parties and d.parties.contact_details and d.parties.contact_details.email)
        or (d.parties and d.parties.claimant and d.parties.claimant.contact and d.parties.claimant.contact.email)),
    ("Contact Address", lambda d: (d.parties and d.parties.contact_details and d.parties.contact_details.address)
        or (d.parties and d.parties.claimant and d.parties.claimant.contact and d.parties.claimant.contact.address)),
    # Asset Details
    ("Asset Type", lambda d: d.asset and d.asset.type),
    ("Asset ID", lambda d: d.asset and d.asset.id),
    ("Estimated Damage", lambda d: (d.asset and d.asset.estimated_damage is not None) and d.asset.estimated_damage
        or (d.status and d.status.initial_estimate is not None) and d.status.initial_estimate),
    # Other Mandatory
    ("Claim Type", lambda d: d.status and d.status.claim_type),
    ("Attachments", lambda d: d.status and d.status.attachments),
    ("Initial Estimate", lambda d: d.status and d.status.initial_estimate),
]


def _is_empty(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, list) and len(val) == 0:
        return True
    return False


def get_missing_fields(doc: FNOLDocument) -> List[str]:
    """Return list of field labels that are missing (empty) in the document."""
    missing: List[str] = []
    for label, getter in CLAIM_FIELD_SPEC:
        try:
            val = getter(doc)
            if _is_empty(val):
                missing.append(label)
        except Exception:
            missing.append(label)
    return missing


def get_extracted_fields_flat(doc: FNOLDocument) -> dict:
    """Return a flat dict of field label -> display value for extracted fields only (non-empty)."""
    out = {}
    for label, getter in CLAIM_FIELD_SPEC:
        try:
            val = getter(doc)
            if val is None:
                out[label] = None
            elif isinstance(val, list):
                out[label] = val if val else None
            else:
                out[label] = str(val) if val else None
        except Exception:
            out[label] = None
    return out


def build_standard_output(doc: FNOLDocument, decision: RoutingDecision) -> dict:
    """
    Build the standard output JSON:
    { "extractedFields": {}, "missingFields": [], "recommendedRoute": "", "reasoning": "" }
    """
    extracted = doc.model_dump(mode="json")
    missing = get_missing_fields(doc)
    reasoning_str = " | ".join(decision.reasoning) if decision.reasoning else ""
    return {
        "extractedFields": extracted,
        "missingFields": missing,
        "recommendedRoute": decision.recommended_route,
        "reasoning": reasoning_str,
    }


def get_field_value_for_form(doc: FNOLDocument, label: str) -> Any:
    """Get display value for one field by label (for claim form UI)."""
    for lbl, getter in CLAIM_FIELD_SPEC:
        if lbl == label:
            try:
                val = getter(doc)
                if val is None:
                    return "—"
                if isinstance(val, list):
                    return ", ".join(str(x) for x in val) if val else "—"
                return str(val) if val is not None else "—"
            except Exception:
                return "—"
    return "—"
