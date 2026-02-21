from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class SourceReference(BaseModel):
    sentence: str
    paragraph: int
    context: str


class CharacterAttribute(BaseModel):
    type: str
    value: str
    paragraph: int
    context: str


class CharacterProfile(BaseModel):
    name: str
    mentions: int
    first_appearance: int
    attributes: Dict[str, List[Dict[str, Any]]]
    relationships: Dict[str, List[str]]
    source_references: List[Dict[str, Any]]


class TimelineEvent(BaseModel):
    event_type: str
    description: str
    timestamp: Optional[str]
    paragraph: int
    characters_involved: List[str]


class Inconsistency(BaseModel):
    type: str
    severity: str
    description: str
    evidence: List[Dict[str, Any]]
    suggestion: str


class ManuscriptResponse(BaseModel):
    id: int
    title: str
    word_count: int
    status: str


class AnalysisResponse(BaseModel):
    manuscript_id: int
    characters: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    inconsistencies: List[Dict[str, Any]]
    summary: Dict[str, int]