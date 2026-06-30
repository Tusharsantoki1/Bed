"""Shared schema base classes and small helper response models."""

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for response models read from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str
