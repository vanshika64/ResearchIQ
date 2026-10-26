import re


# Use broad biomedical vocabulary and require research-article structure as well.
# This intentionally runs locally so paper uploads are not sent to another service
# just to determine whether they belong in the user's medical library.
_MEDICAL_TERMS = re.compile(
    r"\b(?:"
    r"medical|medicine|clinical|health(?:care)?|patient|disease|disorder|syndrome|"
    r"diagnos\w*|therap\w*|treat\w*|medicat\w*|pharmac\w*|drug\w*|hospital|"
    r"physician|nurs\w*|epidemiolog\w*|oncolog\w*|cancer|tumou?r|cardiolog\w*|"
    r"neurolog\w*|infection|infectious|vaccine|immunolog\w*|patholog\w*|surger\w*|"
    r"symptom\w*|mortalit\w*|morbidity|biomedical|biomedicine|public health|"
    r"genom\w*|genetic\w*|molecular|protein\w*|cellular|microbiolog\w*|virolog\w*|"
    r"physiolog\w*|anatom\w*|rehabilitat\w*|mental health|nutrition\w*|"
    r"pediatric\w*|paediatric\w*|maternal|radiolog\w*|diagnostic imaging|"
    r"diabetes|asthma|alzheimer\w*|parkinson\w*|covid(?:-19)?|coronavirus|"
    r"influenza|hiv|stroke|arthritis|obesity|hypertension|depression|anxiety|"
    r"clinical trial|health sciences|medical imaging"
    r")\b",
    re.IGNORECASE,
)

_RESEARCH_TERMS = re.compile(
    r"\b(?:abstract|background|objective\w*|aim\w*|method\w*|material\w*|"
    r"result\w*|finding\w*|conclusion\w*|discussion|limitation\w*|"
    r"participant\w*|cohort\w*|randomi[sz]ed|placebo|trial\w*|study|studies|"
    r"research|systematic review|meta-analysis|observational|case-control|"
    r"cross-sectional|prospective|retrospective|manuscript|publication|"
    r"data analysis|statistical analysis|clinical investigation"
    r")\b",
    re.IGNORECASE,
)

_PAPER_ANALYSIS_TERMS = re.compile(
    r"\b(?:paper\w*|study|studies|research|passage\w*|method\w*|finding\w*|"
    r"limitation\w*|summari[sz]\w*|compare|comparison|gap\w*|evidence|"
    r"author\w*|result\w*|objective\w*|conclusion\w*|participant\w*|"
    r"cohort\w*|trial\w*|population|intervention\w*|outcome\w*|report\w*|"
    r"sample size|study design|methodology|effect\w*|strength\w*|weakness\w*|"
    r"risk of bias|contribution\w*|purpose|significan\w*)\b",
    re.IGNORECASE,
)

_CLEARLY_UNRELATED_TERMS = re.compile(
    r"\b(?:football|soccer|basketball|baseball|cricket|election\w*|politician\w*|"
    r"stock market|cryptocurrency|bitcoin|recipe\w*|cooking|movie\w*|film\w*|"
    r"celebrity|weather|travel|vacation|video game\w*|gaming|car repair|"
    r"homework|algebra|calculus|capital of|president of|fashion|real estate)\b",
    re.IGNORECASE,
)

_RESEARCH_GAP_REQUEST = re.compile(
    r"\b(?:research\s+gaps?|gap\s+analysis|gaps?\s+in\s+(?:the\s+)?(?:literature|research|"
    r"(?:this|these|the)\s+(?:paper|study|papers|studies))|"
    r"(?:find|identify|suggest|infer|what\s+are)\s+(?:the\s+)?(?:possible\s+)?research\s+gaps?|"
    r"unexplored\s+(?:research\s+)?(?:areas?|topics?|questions?)|understudied|under-researched)\b",
    re.IGNORECASE,
)


def is_medical_research_paper(title: str, text: str) -> bool:
    """Require both biomedical subject matter and recognizable research content."""
    sample = f"{title}\n{text[:30000]}"
    return bool(_MEDICAL_TERMS.search(sample) and _RESEARCH_TERMS.search(sample))


def is_medical_research_query(query: str) -> bool:
    """Allow medical topics or ordinary analysis prompts about selected papers."""
    if _MEDICAL_TERMS.search(query):
        return True
    if _CLEARLY_UNRELATED_TERMS.search(query):
        return False
    return bool(_PAPER_ANALYSIS_TERMS.search(query))


def is_research_gap_request(query: str) -> bool:
    """Identify requests for the removed research-gap analysis feature."""
    return bool(_RESEARCH_GAP_REQUEST.search(query))
