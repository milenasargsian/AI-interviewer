import json
import re

from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough


def analyze_cv(cv_text: str, api_key: str) -> dict:
    """
    Analyze CV text using RAG pipeline.
    Uses Groq LLM (free) + local HuggingFace embeddings + Chroma vector store.
    Covers: RAG pipeline + LangChain components + content classification.
    """
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        groq_api_key=api_key,
        temperature=0.1,
    )

    # Local embeddings — downloads ~90MB once, cached automatically
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents([cv_text])
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="cv_analysis",
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    rag_prompt = PromptTemplate.from_template("""
Use the following CV excerpts to answer the question accurately.

CV Content:
{context}

Question: {question}

Return ONLY a valid JSON object — no markdown, no backticks, no explanation:
{{
  "name": "Full name of the candidate",
  "seniority": "junior or mid or senior",
  "job_role": "Most relevant job title",
  "top_skills": ["skill1", "skill2", "skill3", "skill4", "skill5"],
  "years_experience": 3,
  "notable_projects": ["Project description 1", "Project description 2"],
  "skill_gaps": ["Gap 1", "Gap 2"],
  "education": "Highest degree and field",
  "languages": ["Python", "English"],
  "certifications": ["cert1"]
}}

Rules:
- seniority must be exactly one of: junior, mid, senior
- years_experience must be an integer
- all list values must be strings
- if information is missing use empty list [] or "Unknown"
""")

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | rag_prompt
        | llm
        | StrOutputParser()
    )

    query = "Extract all candidate information: name, skills, experience, projects, education, seniority level."
    raw = rag_chain.invoke(query)

    # Parse JSON
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)

    if not json_match:
        fallback = llm.invoke([HumanMessage(
            content=f"Extract candidate info as JSON from this CV:\n\n{cv_text[:3000]}\n\n"
                    f"Return only valid JSON with keys: name, seniority, job_role, "
                    f"top_skills, years_experience, notable_projects, skill_gaps, "
                    f"education, languages, certifications."
        )])
        json_match = re.search(r"\{.*\}", fallback.content, re.DOTALL)

    if not json_match:
        raise ValueError("Could not extract structured data from CV.")

    cv_data = json.loads(json_match.group())

    defaults = {
        "name": "Candidate",
        "seniority": "mid",
        "job_role": "Software Engineer",
        "top_skills": [],
        "years_experience": 0,
        "notable_projects": [],
        "skill_gaps": [],
        "education": "Unknown",
        "languages": [],
        "certifications": [],
    }
    for key, default in defaults.items():
        if key not in cv_data or cv_data[key] is None:
            cv_data[key] = default

    cv_data["seniority"] = determine_seniority(
        years=cv_data.get("years_experience", 0),
        skills=cv_data.get("top_skills", []),
        llm_guess=cv_data.get("seniority", "mid"),
    )

    return cv_data


def determine_seniority(years: int, skills: list, llm_guess: str) -> str:
    """
    Rule-based seniority classification with skill-based exceptions.
    - 0-2 years   -> junior  (unless skills strongly suggest otherwise)
    - 2.5-4 years -> mid
    - 5+ years    -> senior
    Skills can bump up one level if candidate shows advanced expertise.
    """
    senior_keywords = {
        "architecture", "architect", "lead", "principal", "staff",
        "microservices", "kubernetes", "system design", "distributed",
        "leadership", "mentoring", "terraform", "devops", "cto", "vp",
    }
    mid_keywords = {
        "docker", "ci/cd", "rest api", "sql", "react", "node",
        "django", "flask", "spring", "aws", "azure", "gcp",
        "testing", "agile", "scrum", "git",
    }

    skills_lower = {s.lower() for s in skills}
    senior_matches = len(skills_lower & senior_keywords)
    mid_matches    = len(skills_lower & mid_keywords)

    # Base level from years
    if years <= 2:
        base = "junior"
    elif years <= 4:
        base = "mid"
    else:
        base = "senior"

    # Skill-based exceptions — bump up one level max
    if base == "junior" and senior_matches >= 2:
        return "mid"   # junior years but clearly advanced skills
    if base == "junior" and mid_matches >= 3:
        return "mid"   # enough practical tools to be mid
    if base == "mid" and senior_matches >= 3:
        return "senior"  # mid years but senior-level skill set

    # Use LLM guess as tiebreaker only when years are borderline (exactly 2 or 5)
    if years in [2, 5] and llm_guess in ["junior", "mid", "senior"]:
        return llm_guess

    return base
