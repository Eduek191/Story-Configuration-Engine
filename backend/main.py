"""
Story Consistency Engine - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
import uvicorn
import os
from datetime import datetime

from database import Database
from models import (
    ManuscriptResponse,
    CharacterProfileResponse,
    TimelineEventResponse,
    InconsistencyResponse,
    AnalysisStatusResponse,
)
from services.extraction_service import ExtractionService
from services.timeline_service import TimelineService
from services.inconsistency_detector import InconsistencyDetector
from utils.file_handler import FileHandler

# Initialize FastAPI app
app = FastAPI(
    title="Story Consistency Engine API",
    description="Analyze fiction manuscripts for character consistency and timeline logic",
    version="1.0.0",
)

# CORS configuration - Allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
db = Database()
extraction_service = ExtractionService()
timeline_service = TimelineService(db)
inconsistency_detector = InconsistencyDetector(db)
file_handler = FileHandler()

# Ensure upload directory exists
os.makedirs("uploads", exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize database and load NLP models on startup"""
    db.initialize_tables()
    extraction_service.load_models()


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Story Consistency Engine",
        "version": "1.0.0",
    }


@app.post("/api/manuscripts/upload", response_model=ManuscriptResponse)
async def upload_manuscript(
    background_tasks: BackgroundTasks, file: UploadFile = File(...)
):
    """
    Upload a manuscript file for analysis
    Supports .txt, .doc, .docx formats
    """
    try:
        # Validate file type
        if not file_handler.validate_file_type(file.filename):
            raise HTTPException(
                status_code=400,
                detail="Invalid file type. Supported formats: .txt, .doc, .docx",
            )

        # Save uploaded file
        file_path = await file_handler.save_upload(file)

        # Extract text content
        content = await file_handler.extract_text(file_path)

        # Create manuscript record
        manuscript_id = db.create_manuscript(
            title=file.filename, content=content, file_path=file_path
        )

        # Trigger background analysis
        background_tasks.add_task(analyze_manuscript, manuscript_id, content)

        return ManuscriptResponse(
            id=manuscript_id,
            title=file.filename,
            status="processing",
            uploaded_at=datetime.utcnow().isoformat(),
            word_count=len(content.split()),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def analyze_manuscript(manuscript_id: int, content: str):
    """Background task to analyze manuscript"""
    try:
        # Update status to processing
        db.update_manuscript_status(manuscript_id, "processing")

        # Step 1: Extract characters and attributes
        characters = extraction_service.extract_characters(content, manuscript_id)
        for char in characters:
            db.save_character(char, manuscript_id)

        # Step 2: Build timeline
        events = timeline_service.extract_timeline_events(content, manuscript_id)
        for event in events:
            db.save_timeline_event(event, manuscript_id)

        # Step 3: Detect inconsistencies
        inconsistencies = inconsistency_detector.detect_all_inconsistencies(
            manuscript_id
        )
        for inconsistency in inconsistencies:
            db.save_inconsistency(inconsistency, manuscript_id)

        # Update status to completed
        db.update_manuscript_status(manuscript_id, "completed")

    except Exception as e:
        db.update_manuscript_status(manuscript_id, "failed")
        print(f"Analysis failed: {str(e)}")


@app.get(
    "/api/manuscripts/{manuscript_id}/status", response_model=AnalysisStatusResponse
)
async def get_analysis_status(manuscript_id: int):
    """Get the current status of manuscript analysis"""
    manuscript = db.get_manuscript(manuscript_id)

    if not manuscript:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    stats = db.get_manuscript_statistics(manuscript_id)

    return AnalysisStatusResponse(
        manuscript_id=manuscript_id,
        status=manuscript["status"],
        character_count=stats["character_count"],
        event_count=stats["event_count"],
        inconsistency_count=stats["inconsistency_count"],
    )


@app.get(
    "/api/manuscripts/{manuscript_id}/characters",
    response_model=List[CharacterProfileResponse],
)
async def get_characters(manuscript_id: int):
    """Get all extracted characters with their profiles"""
    characters = db.get_characters(manuscript_id)

    response = []
    for char in characters:
        attributes = db.get_character_attributes(char["id"])
        mentions = db.get_character_mentions(char["id"])

        response.append(
            CharacterProfileResponse(
                id=char["id"],
                name=char["name"],
                first_mention=char["first_mention"],
                mention_count=char["mention_count"],
                attributes=attributes,
                source_references=mentions,
            )
        )

    return response


@app.get(
    "/api/manuscripts/{manuscript_id}/timeline",
    response_model=List[TimelineEventResponse],
)
async def get_timeline(manuscript_id: int):
    """Get story timeline with all events"""
    events = db.get_timeline_events(manuscript_id)

    return [
        TimelineEventResponse(
            id=event["id"],
            event_type=event["event_type"],
            description=event["description"],
            character_name=event["character_name"],
            timestamp=event["timestamp"],
            chapter=event["chapter"],
            source_text=event["source_text"],
        )
        for event in events
    ]


@app.get(
    "/api/manuscripts/{manuscript_id}/inconsistencies",
    response_model=List[InconsistencyResponse],
)
async def get_inconsistencies(manuscript_id: int, severity: Optional[str] = None):
    """Get all detected inconsistencies, optionally filtered by severity"""
    inconsistencies = db.get_inconsistencies(manuscript_id, severity)

    return [
        InconsistencyResponse(
            id=inc["id"],
            type=inc["type"],
            severity=inc["severity"],
            description=inc["description"],
            character_name=inc["character_name"],
            location1=inc["location1"],
            location2=inc["location2"],
            suggested_fix=inc["suggested_fix"],
        )
        for inc in inconsistencies
    ]


@app.get("/api/manuscripts")
async def list_manuscripts():
    """List all uploaded manuscripts"""
    manuscripts = db.get_all_manuscripts()
    return manuscripts


@app.delete("/api/manuscripts/{manuscript_id}")
async def delete_manuscript(manuscript_id: int):
    """Delete a manuscript and all associated data"""
    success = db.delete_manuscript(manuscript_id)

    if not success:
        raise HTTPException(status_code=404, detail="Manuscript not found")

    return {"message": "Manuscript deleted successfully"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=True)