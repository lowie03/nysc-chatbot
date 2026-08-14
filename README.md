# Corper Desk — an NYSC assistant for prospective corps members

A question-answering assistant for Nigerians awaiting or undergoing NYSC service.
Ask it about registration, orientation camp, allowances, certificates or your
posting, and it answers from official NYSC sources — or tells you plainly when it
doesn't know, and where to check instead.

**Fellow:** [Godwin Praise (FE/25/8682152521)] · **Track:** [AI & MACHINE LEARNING NEXTGEN COHORT] · **Brief:** [AI-09]

---

## The problem

Prospective corps members rely on WhatsApp rumours and outdated blog posts for
information that determines where they live for a year and what they get paid.
The official NYSC website has the answers, but they're spread across ~25 pages
written in institutional prose. Existing "NYSC chatbots" mostly answer confidently
whether or not they know — which is worse than useless when someone is about to
travel across the country.

Corper Desk is built around one principle: **an answer you can trust because the
system knows the limits of what it knows.**

## What it does

- Answers NYSC questions from a curated corpus drawn from official sources
- Understands Nigerian Pidgin ("wetin be allawee?"), typos, and acronyms (PPA, CDS, SAED)
- Says explicitly when a detail isn't in its data, then links to nysc.gov.ng or the
  relevant state secretariat rather than guessing
- Refuses off-topic questions instead of forcing an answer
- Summarises health facility coverage for any state or LGA, for corps members posted
  somewhere unfamiliar
- Runs entirely free — no API keys, no paid services, no LLM required

## Architecture

User question
│
▼
Preprocessing ─────────── Pidgin glossary, acronym expansion, typo correction
│
▼
Routing ──── health-facility question? ──► pandas query over survey data
│ (exact counts, not similarity)
▼ otherwise
Semantic retrieval ────── sentence-transformers embeddings, cosine similarity
│
▼
Entity filtering ──────── metadata rules: a question naming Imo can't be answered
│ by an Abia fact; a general question can't be answered
│ by any state-specific fact
▼
Confidence tiering ────── ANSWER / PARTIAL / REFUSE, by similarity score
│
▼
Response ──────────────── answer + provenance + suggested follow-ups

### Key design decisions

**Retrieval over a knowledge base, not FAQ matching.** There are no stored
question–answer pairs driving this. Facts are retrieved from a mixed corpus, so the
assistant can answer questions nobody wrote down in advance.

**Chunked one fact per document.** Retrieval accuracy depends on chunk granularity.
A whole-state paragraph would dilute the match for "how much does Oyo pay?"; a single
fact per chunk means the question lands almost exactly on its answer.

**Hybrid retrieval: vectors plus metadata filters.** Cosine similarity cannot express
"must be about Imo" — that's a boolean constraint, not a similarity gradient. Every
document carries a `state` field, and filtering on it before answering is what stops
the 37 near-identical camp addresses from contaminating each other.

**Confidence tiering instead of a binary answer/refuse gate.** A question can be
on-topic and still unanswerable from the data ("who is the Imo coordinator?"). Those
land in a middle tier that admits the gap and points to an authoritative source.

**No generative fallback.** The assistant never invents an answer it doesn't have.
Everything it says is traceable to a corpus entry, and unknowns are handed off to
official channels.

## Data sources

| Source                        | Contents                                                             | Notes                                                              |
| ----------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Kaggle NYSC dataset (states)  | Camp addresses, secretariats, governors, state allowances            | Governors were ~2022 and factually wrong; refreshed and documented |
| nysc.gov.ng                   | Service year, registration rules, FAQs, certification, welfare, SAED | Curated into standalone fact statements                            |
| Kaggle NMIS health facilities | 34,139 facilities with services, staffing, infrastructure            | **2014 survey** — every answer carries that caveat                 |
| Federal allowance             | ₦77,000/month                                                        | From news reporting; not published on nysc.gov.ng                  |

**Data honesty:** raw downloads are never edited. Cleaning happens in code
(`app/loaders.py`) so every transformation is documented and repeatable. The one
corrected file (governors) is a new, versioned file with a Notes & Sources sheet
recording what changed and why.

## Known limitations

- **State allowance figures are unreliable.** Most date from ~2022; only a few states
  have published recent numbers. State top-ups change without notice.
- **Health facility data is from 2014.** Answers are aggregate and directional, never
  facility-level medical guidance.
- **Time-sensitive information is deliberately excluded.** Batch dates and deadlines
  are answered with a pointer to the official timetable rather than a stale copy.
- **Multi-entity questions** ("compare Imo and Abia camps") resolve to one entity.
- **No conversational memory** — each question is answered independently. [Remove this
  line if you shipped query rewriting.]

## Running it

**Requirements:** Python 3.11+, Node 18+

```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload                        # http://localhost:8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

**Production build:** `cd frontend && npm run build` outputs to `backend/static/`,
which FastAPI serves — one process, one port.

No API keys or environment variables are required.

### Endpoints

| Method | Path      | Purpose                                                                         |
| ------ | --------- | ------------------------------------------------------------------------------- |
| POST   | `/chat`   | `{question, history}` → `{answer, tier, sources, followups}`                    |
| POST   | `/debug`  | Same input; returns detected entity, scores, and which facts survived filtering |
| GET    | `/health` | Liveness check and corpus size                                                  |

## Testing

```bash
cd backend && pytest -v
```

Tests are organised by expected behaviour, not by function: questions that **must be
answered**, questions that **must hedge**, questions that **must be refused**, and
entity-scoping tests asserting no cross-contamination between states. Every question
the assistant got wrong during development was added here, so the suite doubles as a
regression log and as the evidence used to tune the confidence thresholds.

## Project structure

backend/
├── api/main.py FastAPI app and static mount
├── app/
│ ├── loaders.py reads and cleans every data source
│ ├── preprocess.py Pidgin glossary, acronyms, typo correction
│ ├── retrieval.py embeddings, cosine search, caching
│ ├── bot.py routing, entity filtering, tiering, responses
│ ├── facilities.py structured queries over health survey data
│ └── llm.py answer templating (optional LLM phrasing layer)
├── data/ raw/ (untouched), processed/, curated corpora
└── tests/
frontend/
└── src/ React app: useChat hook, API layer, view components


## What I'd build next

1. **Conversational memory** via query rewriting — resolve "what about Osun?" against
   the previous question before retrieval, keeping retrieval itself stateless.
2. **Map view** for health facilities, using the latitude/longitude already in the data.
3. **WhatsApp or Telegram delivery** — the backend is deliberately independent of the
   HTTP layer, so this is a new adapter rather than a rewrite.
4. **Corpus expansion** driven by logged PARTIAL responses: every hedge is a
   documented gap, which makes improvement measurable rather than guesswork.

## Acknowledgements

Data from the NYSC official website (nysc.gov.ng), the Nigeria MDG Information System
health facility survey, and Kaggle contributor Idoko Emmanuel.
