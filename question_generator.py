import json
import re

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


PROMPT_V1 = PromptTemplate(
    input_variables=["job_role"],
    template="Generate 5 interview questions for a {job_role}.",
)

PROMPT_V2 = PromptTemplate(
    input_variables=["seniority", "job_role", "skills"],
    template="""
    Given a {seniority}-level {job_role} with skills in {skills},
    generate 5 relevant interview questions covering technical and soft skills.
    """,
)

PROMPT_V3 = PromptTemplate(
    input_variables=["seniority", "job_role", "skills", "projects", "gaps", "years"],
    template="""
You are a senior technical interviewer conducting a real job interview.
Generate targeted interview questions for the candidate below.

CANDIDATE PROFILE:
- Level: {seniority}
- Role: {job_role}
- Years of experience: {years}
- Key skills: {skills}
- Notable projects: {projects}
- Potential weak areas: {gaps}

Generate exactly 8 interview questions tailored to this candidate.
Adapt difficulty to their seniority level ({seniority}).
Reference their actual skills and projects where possible.

Return ONLY valid JSON — no markdown, no backticks, no explanation:
{{
  "questions": [
    {{
      "id": 1,
      "type": "technical",
      "difficulty": "medium",
      "topic": "specific skill or topic",
      "question": "Full question text here?"
    }}
  ]
}}

Question mix: 4 technical, 2 behavioural, 2 situational.
Difficulty: junior=basic, mid=trade-offs, senior=architecture/leadership.
""",
)


def generate_questions(cv_data: dict, api_key: str) -> list:
    """Generate interview questions using Prompt V3 via Groq LLM."""
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=api_key,
        temperature=0.7,
    )

    chain = PROMPT_V3 | llm | StrOutputParser()

    result = chain.invoke({
        "seniority": cv_data.get("seniority", "mid"),
        "job_role": cv_data.get("job_role", "Software Engineer"),
        "skills": ", ".join(cv_data.get("top_skills", [])) or "General programming",
        "projects": ", ".join(cv_data.get("notable_projects", [])) or "None listed",
        "gaps": ", ".join(cv_data.get("skill_gaps", [])) or "None identified",
        "years": str(cv_data.get("years_experience", 0)),
    })

    json_match = re.search(r"\{.*\}", result, re.DOTALL)
    if not json_match:
        raise ValueError("Could not parse questions from LLM response.")

    data = json.loads(json_match.group())
    questions = data.get("questions", [])

    if not questions:
        raise ValueError("LLM returned empty questions list.")

    return questions
