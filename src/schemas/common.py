"""Shared schema base classes and small helper response models."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


def validate_pincode(value: Optional[str]) -> Optional[str]:
    """Indian PIN codes are exactly 6 digits. Blank/None means 'not set'."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if not (value.isdigit() and len(value) == 6):
        raise ValueError("Pincode must be exactly 6 digits")
    return value


class ORMModel(BaseModel):
    """Base for response models read from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str
