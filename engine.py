import streamlit as st
import anthropic
import json

# --- PAGE CONFIG ---
st.set_page_config(page_title="Campus Funds AI", page_icon="🎓", layout="centered")

# --- INITIALIZE API ---
try:
    client = anthropic.Anthropic()
except Exception:
    st.error("⚠️ Please set your ANTHROPIC_API_KEY environment variable.")
    st.stop()

# --- BACKEND LOGIC ---
@st.cache_data
def load_scholarships(path: str = "scholarships.json") -> list[dict]:
    """Load scholarships from a JSON file."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"⚠️ Could not find {path}. Make sure it is in the same folder as app.py.")
        st.stop()

def match_scholarships(user_profile: dict, scholarships: list[dict]) -> list[dict]:
    """Calls Claude to match the user profile against the scholarship list."""
    system_prompt = """You are an expert financial aid advisor. You will receive:
1. A user's demographic profile (JSON)
2. A list of available scholarships (JSON)

Your job: analyze each scholarship's requirements against the user's profile and return the TOP 3 best matches.

RULES:
- Respond with ONLY a valid JSON array. No markdown fences, no prose before or after.
- Each item must have EXACTLY these keys:
    "id"               (string, the exact ID from the scholarship data)
    "match_percentage" (integer 0-100)
    "why_you_match"    (one concise sentence)
- Rank from best to worst match.
- Base match_percentage on how many hard requirements the user meets. Do not inflate scores.
- If fewer than 3 scholarships are a reasonable fit, return only the ones that are."""

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
    
    # Safety net: strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.lower().startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        st.error("Claude returned invalid JSON.")
        st.write("Raw Output:", raw)
        raise e

# --- UI FRONTEND ---
st.title("🎓 Campus Funds AI (UMD)")
st.markdown("Enter your reality. Let AI find your funding.")

# Load the data right away
scholarships_data = load_scholarships("scholarships.json")

# Create a lookup dictionary so we can easily grab the full scholarship data by its ID later
scholarship_lookup = {s["id"]: s for s in scholarships_data}

# Data lists for dropdowns
US_STATES = [
    "Maryland", "District of Columbia", "Virginia", "Pennsylvania", "Delaware", 
    "New York", "New Jersey", "Alabama", "Alaska", "Arizona", "Arkansas", 
    "California", "Colorado", "Connecticut", "Florida", "Georgia", "Hawaii", 
    "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana", 
    "Maine", "Massachusetts", "Michigan", "Minnesota", "Mississippi", "Missouri", 
    "Montana", "Nebraska", "Nevada", "New Hampshire", "New Mexico", "North Carolina", 
    "North Dakota", "Ohio", "Oklahoma", "Oregon", "Rhode Island", "South Carolina", 
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", "Washington", 
    "West Virginia", "Wisconsin", "Wyoming"
]

COMMON_MAJORS = [
    "Computer Science / IT", "Engineering", "Business / Finance", 
    "Health Professions / Nursing", "Biological Sciences", "Psychology", 
    "Education", "Communications / Journalism", "Social Sciences", 
    "Visual & Performing Arts", "Other"
]

ETHNICITIES = [
    "Asian / Asian American", "Black / African American", "Hispanic / Latino", 
    "Native American / Alaska Native", "White / Caucasian", 
    "Native Hawaiian / Pacific Islander", "Two or More Races", "Prefer not to say"
]

with st.form("student_profile"):
    st.subheader("Your Profile")
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name", value="Jamie Chen")
        major = st.selectbox("Major", COMMON_MAJORS, index=0)
        gpa = st.number_input("GPA", min_value=0.0, max_value=4.0, value=3.8, step=0.1)
        year = st.selectbox("Year", ["Freshman", "Sophomore", "Junior", "Senior", "Transfer", "Grad Student"], index=1)
        state = st.selectbox("State / Territory", US_STATES, index=0)
        
    with col2:
        ethnicity = st.selectbox("Ethnicity", ETHNICITIES, index=0)
        gender = st.selectbox("Gender", ["Female", "Male", "Non-binary", "Prefer not to say"], index=1)
        financial_need = st.selectbox("Financial Need", ["High", "Medium", "Low"])
        interests = st.text_input("Interests (comma separated)", value="AI, cybersecurity, robotics")

    # Use columns to push the button to the right
    spacer, btn_col = st.columns([4, 1])
    with btn_col:
        submit_button = st.form_submit_button("Find My Funds", use_container_width=True)

# --- EXECUTE ON SUBMIT ---
if submit_button:
    with st.spinner("Claude is analyzing your profile against the database..."):
        
        # Build the dictionary exactly how your backend expects it
        user_profile = {
            "name": name,
            "major": major,
            "school": "University of Maryland",
            "gpa": gpa,
            "year": year,
            "state": state,
            "ethnicity": ethnicity,
            "gender": gender,
            "financial_need": financial_need,
            "interests": [i.strip() for i in interests.split(",")]
        }

        try:
            matches = match_scholarships(user_profile, scholarships_data)
            
            st.success(f"✅ Found top matches for you!")
            
            # Display results dynamically based on your JSON keys
            for match in matches:
                # Use the ID returned by Claude to pull the exact data from our JSON
                s_data = scholarship_lookup.get(match["id"])
                
                # Safety check in case Claude hallucinates an ID
                if not s_data:
                    continue

                # Safely get the values with fallbacks if the JSON is missing keys
                amount_val = s_data.get('amount', 'Amount TBD')
                amount_formatted = f"${int(amount_val):,}" if str(amount_val).isnumeric() else amount_val
                
                deadline = s_data.get('deadline', 'Check website')
                url = s_data.get('source_url', 'https://financialaid.umd.edu/')

                with st.expander(f"**{s_data.get('name', 'Scholarship')}** — {match['match_percentage']}% Match", expanded=True):
                    st.write(f"💡 **Why you match:** {match['why_you_match']}")
                    
                    # Markdown layout for the stats and hyperlink
                    st.markdown(f"""
                    * **Amount:** {amount_formatted}
                    * **Deadline:** {deadline}
                    * **[🔗 Click here to apply]({url})**
                    """)
                    
        except Exception as e:
            st.error(f"Something went wrong: {e}")
