import anthropic
import json

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

def match_scholarships(user_profile: dict, scholarships: list[dict]) -> list[dict]:
    """
    Returns the top 3 scholarship matches for a given user profile.
    
    Args:
        user_profile: dict of demographics (major, GPA, state, ethnicity, etc.)
        scholarships: list of scholarship dicts (name, amount, requirements, etc.)
    
    Returns:
        list of up to 3 matches, each with scholarship_name, match_percentage, why_you_match
    """
    
    system_prompt = """You are an expert financial aid advisor. You will receive:
1. A user's demographic profile (JSON)
2. A list of available scholarships (JSON)

Your job: analyze each scholarship's requirements against the user's profile and return the TOP 3 best matches.

RULES:
- Respond with ONLY a valid JSON array. No markdown fences, no prose before or after.
- Each item must have EXACTLY these keys:
    "scholarship_name" (string)
    "match_percentage" (integer 0-100)
    "why_you_match"    (one concise sentence)
- Rank from best to worst match.
- Base match_percentage on how many hard requirements the user meets AND how specifically the scholarship targets their profile. Do not inflate scores.
- If fewer than 3 scholarships are a reasonable fit, return only the ones that are.

Example output:
[
  {"scholarship_name": "X Award", "match_percentage": 94, "why_you_match": "..."},
  {"scholarship_name": "Y Grant", "match_percentage": 82, "why_you_match": "..."},
  {"scholarship_name": "Z Fund",  "match_percentage": 71, "why_you_match": "..."}
]"""

    user_message = f"""USER PROFILE:
{json.dumps(user_profile, indent=2)}

AVAILABLE SCHOLARSHIPS:
{json.dumps(scholarships, indent=2)}

Return the top 3 matches as a JSON array."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    
    raw = response.content[0].text.strip()
    
    # Safety net: strip markdown fences if Claude sneaks them in
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[!] Couldn't parse JSON. Raw output:\n{raw}")
        raise e


def load_scholarships(path: str = "scholarships.json") -> list[dict]:
    """Load scholarships from a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


# ---------- Quick test ----------
if __name__ == "__main__":
    sample_user = {
        "name": "Jamie Chen",
        "major": "Computer Science",
        "school": "University of Maryland",
        "gpa": 3.8,
        "year": "Sophomore",
        "state": "Maryland",
        "ethnicity": "Asian American",
        "gender": "Female",
        "financial_need": "High",
        "interests": ["AI", "cybersecurity", "robotics"],
    }
    
    # Load the full scholarship dataset from scholarships.json
    scholarships = load_scholarships("scholarships.json")
    print(f"Loaded {len(scholarships)} scholarships from scholarships.json\n")
    
    print(f"Finding top matches for {sample_user['name']}...\n")
    matches = match_scholarships(sample_user, scholarships)
    
    print("=" * 60)
    print("TOP MATCHES")
    print("=" * 60)
    print(json.dumps(matches, indent=2))



