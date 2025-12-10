"""
Defines the AI judges, their scoring models, and their evaluation logic.
"""

import os
import random
import logging
import json
from abc import ABC, abstractmethod
from typing import List, Optional

import openai
import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError

from hotbench.utils import SCORE_CATEGORIES


class JudgeScore(BaseModel):
    """
    Pydantic model for a judge's score, directly reflecting the rubric.
    This structure is what the LLM is expected to return in JSON format.
    """
    effectiveness: int = Field(..., description=f"Score for effectiveness (1-{SCORE_CATEGORIES['effectiveness']})",
                               ge=1, le=SCORE_CATEGORIES['effectiveness'])
    creativity: int = Field(..., description=f"Score for creativity/originality (1-{SCORE_CATEGORIES['creativity']})",
                            ge=1, le=SCORE_CATEGORIES['creativity'])
    scholarship: int = Field(...,
                             description=f"Score for scholarship/craftsmanship (1-{SCORE_CATEGORIES['scholarship']})",
                             ge=1, le=SCORE_CATEGORIES['scholarship'])
    effort: int = Field(..., description=f"Score for effort (1-{SCORE_CATEGORIES['effort']})", ge=1,
                        le=SCORE_CATEGORIES['effort'])
    rationale: str = Field(...,
                           description="Detailed rationale for the scores provided, citing examples from the text.")

    @property
    def total(self) -> int:
        """Calculate the total score."""
        return self.effectiveness + self.creativity + self.scholarship + self.effort


class Judge(ABC):
    """Abstract base class for an AI Judge"""

    def __init__(self, judge_id: int, judge_type: str, model_name: str):
        self.judge_id = judge_id
        self.judge_type = judge_type
        self.model_name = model_name

    @abstractmethod
    def evaluate(self, essay_content: str, student_name: str) -> JudgeScore:
        """Evaluate the essay text and return a JudgeScore."""
        raise NotImplementedError

    @staticmethod
    def _create_prompt(persona: str, essay_content: str) -> str:
        """Creates a standardized prompt for the LLM."""
        rubric_details = "\n".join(
            [f"- {key.capitalize()}: (1-{value} points)" for key, value in SCORE_CATEGORIES.items()])
        json_schema = JudgeScore.model_json_schema()

        return f"""
You are an AI essay judge with the persona of '{persona}'.
Your task is to evaluate a middle school student's essay for a Black History Month contest.

**Rubric:**
{rubric_details}

**Instructions:**
1. Read the essay carefully.
2. Score the essay based on each category in the rubric.
3. Provide a detailed rationale for your scores, citing specific examples from the essay.
4. Respond ONLY with a valid JSON object that conforms to the following schema:

**JSON Schema:**
```json
{json.dumps(json_schema, indent=2)}
```

**Essay to Evaluate:**
---
{essay_content}
---
"""

    @staticmethod
    def _simulate_score(essay_content: str) -> JudgeScore:
        """Deterministic simulated scoring for offline/testing runs."""
        seed = len(essay_content)
        rnd = random.Random(seed)
        return JudgeScore.model_validate(
            {
                "effectiveness": rnd.randint(1, SCORE_CATEGORIES['effectiveness']),
                "creativity": rnd.randint(1, SCORE_CATEGORIES['creativity']),
                "scholarship": rnd.randint(1, SCORE_CATEGORIES['scholarship']),
                "effort": rnd.randint(1, SCORE_CATEGORIES['effort']),
                "rationale": "This is a simulated score generated because no API key was available.",
            }
        )


class OpenAIAcademicJudge(Judge):
    """An academic-focused judge using an OpenAI model."""

    client: Optional[openai.OpenAI]

    def __init__(self, judge_id: int, model_name: str = "gpt-4o-mini"):
        super().__init__(judge_id, "The Academic", model_name)
        if not os.getenv("OPENAI_API_KEY"):
            self.client = None
            logging.warning(
                f"Judge {self.judge_id} ({self.judge_type}): OPENAI_API_KEY not found. Will use simulation.")
        else:
            self.client = openai.OpenAI()

    def _perform_live_evaluation(self, client: openai.OpenAI, prompt: str) -> JudgeScore:
        """Helper method to perform the actual API call."""
        try:
            # Build kwargs dict to handle the response_format typing issue cleanly
            kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            }
            # The type checker understands unpacking a dictionary of arguments
            response = client.chat.completions.create(**kwargs)

            payload = json.loads(response.choices[0].message.content)
            return JudgeScore.model_validate(payload)
        except (openai.OpenAIError, json.JSONDecodeError, ValidationError, KeyError, IndexError):
            logging.exception("OpenAI call or parsing failed; falling back to simulation.")
            # The essay content is not available here, so we create a generic simulation
            return self._simulate_score("")

    def evaluate(self, essay_content: str, student_name: str) -> JudgeScore:
        if not self.client:
            # If no API key is present, fall back to simulation.
            return self._simulate_score(essay_content)
        else:
            # The client is guaranteed to be valid here.
            prompt = self._create_prompt(self.judge_type, essay_content)
            return self._perform_live_evaluation(self.client, prompt)


class GoogleCreativeJudge(Judge):
    """A creativity-focused judge using a Google model."""

    model: Optional[genai.GenerativeModel]

    def __init__(self, judge_id: int, model_name: str = "gemini-2.5-flash"):
        super().__init__(judge_id, "The Creative Writer", model_name)
        if not os.getenv("GOOGLE_API_KEY"):
            self.model = None
            logging.warning(
                f"Judge {self.judge_id} ({self.judge_type}): GOOGLE_API_KEY not found. Will use simulation.")
        else:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = genai.GenerativeModel(self.model_name)

    def _perform_live_evaluation(self, model: genai.GenerativeModel, prompt: str) -> JudgeScore:
        """Helper method to perform the actual API call."""
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            payload = json.loads(response.text)
            return JudgeScore.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, AttributeError, KeyError):
            logging.exception("Google LLM call or parsing failed; falling back to simulation.")
            return self._simulate_score("")

    def evaluate(self, essay_content: str, student_name: str) -> JudgeScore:
        if not self.model:
            # If no API key is present, fall back to simulation.
            return self._simulate_score(essay_content)
        else:
            # The model is guaranteed to be valid here.
            prompt = self._create_prompt(self.judge_type, essay_content)
            return self._perform_live_evaluation(self.model, prompt)


class OpenAIHistoryJudge(Judge):
    """A history professor judge using an OpenAI model."""

    client: Optional[openai.OpenAI]

    def __init__(self, judge_id: int, model_name: str = "gpt-4o-mini"):
        super().__init__(judge_id, "History Professor", model_name)
        if not os.getenv("OPENAI_API_KEY"):
            self.client = None
            logging.warning(
                f"Judge {self.judge_id} ({self.judge_type}): OPENAI_API_KEY not found. Will use simulation.")
        else:
            self.client = openai.OpenAI()

    def _perform_live_evaluation(self, client: openai.OpenAI, prompt: str) -> JudgeScore:
        """Helper method to perform the actual API call."""
        try:
            kwargs = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            }
            response = client.chat.completions.create(**kwargs)
            payload = json.loads(response.choices[0].message.content)
            return JudgeScore.model_validate(payload)
        except (openai.OpenAIError, json.JSONDecodeError, ValidationError, KeyError, IndexError):
            logging.exception("OpenAI call or parsing failed; falling back to simulation.")
            return self._simulate_score("")

    def evaluate(self, essay_content: str, student_name: str) -> JudgeScore:
        if not self.client:
            return self._simulate_score(essay_content)
        else:
            prompt = self._create_prompt(self.judge_type, essay_content)
            return self._perform_live_evaluation(self.client, prompt)


class GoogleLiteratureJudge(Judge):
    """An English Literature professor judge using a Google model."""

    model: Optional[genai.GenerativeModel]

    def __init__(self, judge_id: int, model_name: str = "gemini-2.5-flash"):
        super().__init__(judge_id, "English Literature Professor", model_name)
        if not os.getenv("GOOGLE_API_KEY"):
            self.model = None
            logging.warning(
                f"Judge {self.judge_id} ({self.judge_type}): GOOGLE_API_KEY not found. Will use simulation.")
        else:
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = genai.GenerativeModel(self.model_name)

    def _perform_live_evaluation(self, model: genai.GenerativeModel, prompt: str) -> JudgeScore:
        """Helper method to perform the actual API call."""
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            payload = json.loads(response.text)
            return JudgeScore.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, AttributeError, KeyError):
            logging.exception("Google LLM call or parsing failed; falling back to simulation.")
            return self._simulate_score("")

    def evaluate(self, essay_content: str, student_name: str) -> JudgeScore:
        if not self.model:
            return self._simulate_score(essay_content)
        else:
            prompt = self._create_prompt(self.judge_type, essay_content)
            return self._perform_live_evaluation(self.model, prompt)


def get_all_judges() -> List[Judge]:
    """
    Instantiate and return all configured judges.
    This is the single point of configuration for which judges will participate.
    """
    return [
        OpenAIAcademicJudge(judge_id=1),
        GoogleCreativeJudge(judge_id=2),
        OpenAIHistoryJudge(judge_id=3),
        GoogleLiteratureJudge(judge_id=4),
    ]
