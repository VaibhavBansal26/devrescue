from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from . import inference
from .db import Feedback, Incident, make_session_factory

app = FastAPI(title="DevRescue")
_factory = None


def get_db():
    global _factory
    if _factory is None:
        _factory = make_session_factory()
    s = _factory()
    try:
        yield s
    finally:
        s.close()


class DiagnoseIn(BaseModel):
    kind: Literal["log", "stack_trace", "ci_failure"]
    text: str = Field(min_length=1, max_length=20000)


class DiagnoseOut(BaseModel):
    incident_id: int
    diagnosis: str


class FeedbackIn(BaseModel):
    prompt: str
    response: str
    rating: int = Field(ge=1, le=5)


class ResolveIn(BaseModel):
    root_cause_correct: bool
    fix_minutes: float = Field(ge=0)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/diagnose", response_model=DiagnoseOut)
def diagnose(body: DiagnoseIn, db=Depends(get_db)):
    answer = inference.diagnose(body.kind, body.text)
    inc = Incident(kind=body.kind, input_text=body.text, diagnosis=answer)
    db.add(inc)
    db.commit()
    return DiagnoseOut(incident_id=inc.id, diagnosis=answer)


@app.post("/feedback", status_code=201)
def feedback(body: FeedbackIn, db=Depends(get_db)):
    db.add(Feedback(**body.model_dump()))
    db.commit()
    return {"stored": True}


@app.post("/incidents/{incident_id}/resolve")
def resolve(incident_id: int, body: ResolveIn, db=Depends(get_db)):
    inc = db.get(Incident, incident_id)
    if not inc:
        raise HTTPException(404, "incident not found")
    inc.root_cause_correct = int(body.root_cause_correct)
    inc.fix_minutes = body.fix_minutes
    db.commit()
    return {"ok": True}


@app.get("/metrics")
def metrics(db=Depends(get_db)):
    """Live version of the headline numbers: root-cause accuracy and mean fix time."""
    n, acc, mins = db.query(
        func.count(Incident.root_cause_correct),
        func.avg(Incident.root_cause_correct),
        func.avg(Incident.fix_minutes),
    ).filter(Incident.root_cause_correct.isnot(None)).one()
    return {"resolved_incidents": n, "root_cause_accuracy": acc, "avg_fix_minutes": mins}
