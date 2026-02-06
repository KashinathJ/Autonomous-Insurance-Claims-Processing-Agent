"""
Pydantic v2 schemas for FNOL (First Notice of Loss) structured data.
Used for extraction validation and routing decisions.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

# Type alias to avoid shadowing the field name "date" in Incident (Pydantic schema error)
DateType = date


# --- Policy ---
class Policy(BaseModel):
    """Policy information from the claim."""

    number: Optional[str] = Field(None, description="Policy number")
    holder_name: Optional[str] = Field(None, description="Policy holder full name")
    effective_date_start: Optional[date] = Field(None, description="Policy effective start date")
    effective_date_end: Optional[date] = Field(None, description="Policy effective end date")


# --- Incident ---
class Incident(BaseModel):
    """Incident details."""

    date: Optional[DateType] = Field(None, description="Date of incident")
    time: Optional[str] = Field(None, description="Time of incident")
    location: Optional[str] = Field(None, description="Incident location/address")
    description: Optional[str] = Field(None, description="Incident description")


# --- Parties ---
class ContactDetails(BaseModel):
    """Contact information for a party."""

    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None


class Party(BaseModel):
    """A party involved in the claim (claimant or third party)."""

    name: Optional[str] = None
    role: Optional[str] = None  # e.g. "claimant", "third_party", "witness"
    contact: Optional[ContactDetails] = None


class Parties(BaseModel):
    """All parties: claimant, third parties, contact details."""

    claimant: Optional[Party] = None
    third_parties: list[Party] = Field(default_factory=list)
    contact_details: Optional[ContactDetails] = Field(None, description="Primary contact for the claim")


# --- Asset ---
class Asset(BaseModel):
    """Claimed asset and damage estimate."""

    type: Optional[str] = Field(None, description="Asset type, e.g. vehicle, property")
    id: Optional[str] = Field(None, description="Asset identifier or VIN etc.")
    estimated_damage: Optional[float] = Field(None, description="Estimated damage amount in currency units")
    currency: Optional[str] = Field("USD", description="Currency for estimated_damage")


# --- Status ---
class Status(BaseModel):
    """Claim status and metadata."""

    claim_type: Optional[str] = Field(None, description="e.g. property, injury, auto")
    attachments: list[str] = Field(default_factory=list, description="List of attachment names/descriptions")
    initial_estimate: Optional[float] = Field(None, description="Initial estimate amount")
    initial_estimate_currency: Optional[str] = Field(default="USD", description="Currency for initial estimate")


# --- Top-level FNOL Document ---
class FNOLDocument(BaseModel):
    """
    Decision-ready FNOL (First Notice of Loss) document.
    All fields are optional at extraction level; validation and routing
    use them to determine mandatory field completeness.
    """

    policy: Optional[Policy] = None
    incident: Optional[Incident] = None
    parties: Optional[Parties] = None
    asset: Optional[Asset] = None
    status: Optional[Status] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
        }
