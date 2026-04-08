from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

TriageLevel = Literal["RED", "ORANGE", "GREEN"]


class IntakeRequest(BaseModel):
    patient_name: str = Field(default="", max_length=200)
    chief_complaint_text: str = Field(default="", max_length=2000)
    symptoms: Dict[str, int]  # 0..5 for each symptom key
    use_nlp_extraction: bool = True
    clarification_completed: bool = False
    age_group: Optional[str] = None
    sex: Optional[str] = None
    pregnant: Optional[bool] = None
    chronic_illnesses: List[str] = []
    chronic_illnesses_other: str = Field(default="", max_length=500)


class SelectedSymptom(BaseModel):
    symptom: str
    rating: int


class ExtractedSymptom(BaseModel):
    symptom: str
    rating: int
    confidence: float
    source_phrase: str


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
    extracted_symptoms: List[ExtractedSymptom] = []
    matched_rules: List[MatchedRule]
    advice_blocks: List[str]
    needs_clarification: bool = False
    follow_up_questions: List[FollowUpQuestion] = []


class TriageLogResponse(BaseModel):
    session_id: str
    triage_level: TriageLevel
    created_at: str
    request_payload: Dict[str, Any]
    response_payload: Dict[str, Any]
