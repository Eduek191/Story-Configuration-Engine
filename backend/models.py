"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ManuscriptResponse(BaseModel):
    id: int
    title: str
    status: str
    uploaded_at: str
    word_count: int


class AnalysisStatusResponse(BaseModel):
    manuscript_id: int
    status: str
    character_count: int
    event_count: int
    inconsistency_count: int


class CharacterAttribute(BaseModel):
    type: str
    value: str
    source: Optional[str] = None
    confidence: float = 1.0


class CharacterMention(BaseModel):
    chapter: Optional[int] = None
    paragraph: Optional[int] = None
    sentence_text: str
    context: str


class CharacterProfileResponse(BaseModel):
    id: int
    name: str
    first_mention: str
    mention_count: int
    attributes: List[Dict[str, Any]]
    source_references: List[Dict[str, Any]]


class TimelineEventResponse(BaseModel):
    id: int
    event_type: str
    description: str
    character_name: Optional[str] = None
    timestamp: Optional[str] = None
    chapter: Optional[int] = None
    source_text: str


class InconsistencyResponse(BaseModel):
    id: int
    type: str
    severity: str
    description: str
    character_name: Optional[str] = None
    location1: Optional[str] = None
    location2: Optional[str] = None
    suggested_fix: Optional[str] = None