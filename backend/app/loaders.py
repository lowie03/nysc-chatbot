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

# Only these 4 raw columns ever get read downstream (app/facilities.py, app/bot.py) —
# the survey has ~29 columns total, so restricting to these at parse time (rather
# than loading everything and dropping most of it after) is a real memory win,
# not just tidiness. This matters on memory-constrained hosts (e.g. Render's free
# 512Mi tier), where loading all 29 columns of a 34k-row CSV at startup alongside
# the embedding model can be the difference between booting and OOM-killed.
_FACILITY_COLUMNS = ["unique_lga", "facility_type_display", "num_doctors_fulltime", "management"]


def load_health_facilities(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8", usecols=_FACILITY_COLUMNS)

    df["num_doctors_fulltime"] = pd.to_numeric(df["num_doctors_fulltime"], errors="coerce")

    parts = df["unique_lga"].str.rsplit("_", n=1, expand=True)
    df["state"] = parts[0].str.replace("_", " ").str.title()
    df["lga"] = parts[1].str.title()

    return df.drop(columns=["unique_lga"])
