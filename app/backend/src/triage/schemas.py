from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

TriageLevel = Literal["RED", "ORANGE", "GREEN"]

# 0 = none, 1 = mild, 2 = moderate, 3 = severe. Must match rules.json "rating_scale".
SymptomRating = Annotated[int, Field(ge=0, le=3)]

# Kiosk intake is filled by the patient, an accompanying person, or a nurse as a fallback.
EnteredBy = Literal["patient", "companion", "nurse"]


class IntakeRequest(BaseModel):
    patient_name: str = Field(default="", max_length=200)
    chief_complaint_text: str = Field(default="", max_length=2000)
    symptoms: Dict[str, SymptomRating]
    use_nlp_extraction: bool = True
    clarification_completed: bool = False
    entered_by: Optional[EnteredBy] = None
    age_group: Optional[Literal["child", "adult", "elderly"]] = None
    sex: Optional[Literal["female", "male", "other"]] = None
    pregnant: Optional[bool] = None
    chronic_illnesses: List[str] = Field(default_factory=list)
    chronic_illnesses_other: str = Field(default="", max_length=500)


class SelectedSymptom(BaseModel):
    symptom: str
    rating: int


class ExtractedSymptom(BaseModel):
    symptom: str
    rating: int
    confidence: float
    source_phrase: str


class ExtractedEntity(BaseModel):
    text: str
    label: str
    score: float


class MatchedRule(BaseModel):
    id: str
    reason: str


class FollowUpQuestion(BaseModel):
    question_id: str
    symptom: str
    question_text: str
    suggested_rating_if_yes: int = 2


class TriageResponse(BaseModel):
    session_id: str
    triage_level: TriageLevel
    selected_symptoms: List[SelectedSymptom]
    extracted_symptoms: List[ExtractedSymptom] = Field(default_factory=list)
    extracted_entities: List[ExtractedEntity] = Field(default_factory=list)
    matched_rules: List[MatchedRule]
    advice_blocks: List[str]
    needs_clarification: bool = False
    follow_up_questions: List[FollowUpQuestion] = Field(default_factory=list)


class TriageLogResponse(BaseModel):
    session_id: str
    triage_level: TriageLevel
    created_at: str
    request_payload: Dict[str, Any]
    response_payload: Dict[str, Any]


class TriageQueueItem(BaseModel):
    session_id: str
    triage_level: TriageLevel
    created_at: str
    patient_name: str = ""
    age_group: Optional[str] = None
    sex: Optional[str] = None
    entered_by: Optional[str] = None
    chief_complaint_text: str = ""


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    token: str
    username: str
    display_name: str
    expires_at: int


class TranscriptionResponse(BaseModel):
    text: str
