from pydantic import BaseModel, Field

class QuestionRequest(BaseModel):
    question1: str = Field(max_length=1000)