"""Load and clean all data sources. Raw files are never modified."""
import json
import pandas as pd


# ---------- States (Excel) ----------

def load_states(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="NYSC Data")
    df["state_name"] = df["State"].str.replace(" State", "", regex=False).str.strip()
    return df


def build_corpus(df: pd.DataFrame) -> list[dict]:
    """Each state row becomes several small fact-documents (chunking)."""
    docs = []
    for _, r in df.iterrows():
        display = r["State"]        # e.g. "Abia State" or "Abuja" — used in prose
        state = r["state_name"]     # e.g. "Abia" or "Abuja" — normalized key
        facts = {
            "camp": f"{display} orientation camp address: {r['Orientation Camp Address']}",
            "secretariat": f"The NYSC secretariat in {display}: {r['NYSC Secretariat']}",
            "governor": f"The current governor of {display} is {r['Current Governor']}.",
            "slogan": f"{display} is known as '{r['State Title']}'.",
        }
        if pd.notna(r["State Allowance"]):
            facts["allowance"] = (
                f"{display} pays corps members a state allowance of "
                f"₦{int(r['State Allowance']):,} per month, "
                f"in addition to the federal allowance."
            )
        for topic, text in facts.items():
            docs.append({"id": f"{state.lower().replace(' ', '_')}_{topic}",
                         "state": state, "topic": topic, "text": text})
    return docs


# ---------- General facts (JSONL) ----------

def load_general_facts(path: str) -> list[dict]:
    """Nationwide facts — no single entity owns these, so state is always None."""
    with open(path, encoding="utf-8") as f:
        docs = [json.loads(line) for line in f if line.strip()]
    for doc in docs:
        doc["state"] = None
    return docs


# ---------- FAQs (JSONL) ----------

def load_faqs(path: str) -> list[dict]:
    """Official NYSC FAQ pairs — nationwide, so state is always None. The
    question is folded into embed_text so a user's phrasing can match the
    stored question directly, not just the answer prose; text (the answer)
    is left untouched since that's what gets shown to the user."""
    with open(path, encoding="utf-8") as f:
        docs = [json.loads(line) for line in f if line.strip()]
    for doc in docs:
        doc["state"] = None
        doc["embed_text"] = f"{doc['question']} {doc['text']}"
    return docs


# ---------- Health facilities (CSV) ----------

def load_health_facilities(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")

    bool_cols = [
        "maternal_health_delivery_services", "emergency_transport",
        "skilled_birth_attendant", "phcn_electricity", "c_section_yn",
        "child_health_measles_immun_calc", "improved_water_supply",
        "improved_sanitation", "vaccines_fridge_freezer",
        "antenatal_care_yn", "family_planning_yn",
        "malaria_treatment_artemisinin",
    ]
    for col in bool_cols:
        df[col] = df[col].map({True: True, "True": True, False: False, "False": False})
        # NaN stays NaN: unknown is unknown, not False

    staff_cols = ["num_doctors_fulltime", "num_nurses_fulltime",
                  "num_nursemidwives_fulltime", "num_chews_fulltime"]
    df[staff_cols] = df[staff_cols].apply(pd.to_numeric, errors="coerce")

    parts = df["unique_lga"].str.rsplit("_", n=1, expand=True)
    df["state"] = parts[0].str.replace("_", " ").str.title()
    df["lga"] = parts[1].str.title()

    return df.drop(columns=["gps", "formhub_photo_id", "survey_id", "sector"])
