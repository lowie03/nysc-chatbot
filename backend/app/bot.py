"""The chatbot core: route → retrieve/query → answer."""
import re

import pandas as pd
from app import llm
from app.loaders import (load_states, build_corpus, load_faqs,
                         load_general_facts, load_health_facilities)
from app.retrieval import Retriever, CONFIDENCE_LOW, CONFIDENCE_HIGH

FALLBACK = ("This bot only covers NYSC topics — things like registration, "
            "orientation camp, allowances, and the service year. If your "
            "question is about something else, a web search is probably "
            "faster. For official NYSC matters this bot doesn't have data on, "
            "check nysc.gov.ng or call the NYSC Distress Call Centre short "
            "code 6972.")

PARTIAL_PREFIX = "I don't have that specific detail in my data — here's what I do have:"

_FACT_SPREAD = 0.06   # tighter than before: entity filtering already removed
                       # the legitimate near-ties, so what's left over should
                       # be a real tie, not a sibling entity riding along

_HEALTH_KEYWORDS = ("hospital", "clinic", "health facilit", "health centre",
                    "health center", "phc", "healthcare")

_HEALTH_SOURCE = {"label": "2014 national health facility survey", "url": None, "phone": None}
_STATE_RECORDS_SOURCE = {"label": "NYSC state records", "url": None, "phone": None}
_GOVNG_SOURCE = {"label": "Check nysc.gov.ng", "url": "https://www.nysc.gov.ng/", "phone": None}
_DISTRESS_SOURCE = {"label": "NYSC Distress Call Centre", "url": None, "phone": "6972"}

_PHONE_RE = re.compile(r"Tel:\s*(\d+)")

FOLLOWUPS_BY_TOPIC = {
    "allowance": [
        {"label": "What does my state add?",
         "query": "What state allowance do states pay corps members?"},
        {"label": "When is it paid?",
         "query": "When is the NYSC allowance paid each month?"},
    ],
    "camp": [
        {"label": "How long does orientation camp last?",
         "query": "How long does NYSC orientation camp last?"},
        {"label": "What should I pack for camp?",
         "query": "What activities happen during NYSC orientation camp?"},
    ],
    "governor": [
        {"label": "What is my state known for?",
         "query": "What is my state's title or slogan?"},
        {"label": "Where is the state secretariat?",
         "query": "Where is the NYSC state secretariat located?"},
    ],
    "secretariat": [
        {"label": "Where is the orientation camp?",
         "query": "Where is the NYSC orientation camp located?"},
        {"label": "How much is my state allowance?",
         "query": "How much state allowance does my state pay corps members?"},
    ],
    "registration": [
        {"label": "What documents do I need?",
         "query": "What documents do I need for NYSC registration?"},
        {"label": "How do I get my call-up letter?",
         "query": "How do I get my NYSC call-up letter?"},
    ],
    "orientation_camp": [
        {"label": "How long is orientation camp?",
         "query": "How long does NYSC orientation camp last?"},
        {"label": "What happens after camp?",
         "query": "What happens after NYSC orientation camp ends?"},
    ],
    "cds": [
        {"label": "What is a PPA?",
         "query": "What is a Place of Primary Assignment in NYSC?"},
        {"label": "How long is the service year?",
         "query": "How long is the NYSC service year?"},
    ],
    "contact": [
        {"label": "Where is the NYSC headquarters?",
         "query": "Where is the NYSC headquarters located?"},
        {"label": "What is the distress line?",
         "query": "What is the NYSC distress call centre number?"},
    ],
    "service_year": [
        {"label": "What are the four segments of service?",
         "query": "What are the four segments of the NYSC service year?"},
        {"label": "When is passing-out?",
         "query": "When does the NYSC passing-out ceremony happen?"},
    ],
    "ppa": [
        {"label": "Can I reject my posting?",
         "query": "Can a corps member reject their NYSC posting?"},
        {"label": "What is CDS?",
         "query": "What is Community Development Service in NYSC?"},
    ],
}


class NYSCBot:
    def __init__(self):
        docs = build_corpus(load_states("data/processed/NYSC.xlsx"))
        docs += load_general_facts("data/general_facts.jsonl")
        docs += load_faqs("data/faqs.jsonl")
        self.retriever = Retriever(docs)
        self.facilities = load_health_facilities("data/raw/health-facilities-in-nigeria.csv")
        self.states = sorted(self.facilities["state"].dropna().unique())
        self._secretariat_phones = self._build_phone_lookup(docs)
        self.state_names = sorted({d["state"] for d in docs if d.get("state") is not None})

    @staticmethod
    def _build_phone_lookup(docs: list[dict]) -> dict:
        phones = {}
        for doc in docs:
            if doc.get("topic") == "secretariat":
                match = _PHONE_RE.search(doc["text"])
                if match:
                    phones[doc["state"]] = match.group(1)
        return phones

    def _detect_entity(self, question: str) -> str | None:
        """Entity named in the question, matched on word boundaries so short
        names (e.g. 'Niger') can't match inside longer words (e.g. 'Nigeria')."""
        matches = [name for name in self.state_names
                   if re.search(rf"\b{re.escape(name)}\b", question, re.I)]
        if not matches:
            return None
        return max(matches, key=len)

    def _filter_hits(self, hits: list[dict], question: str) -> list[dict]:
        """Metadata-aware eligibility filter: entity scope decides what CAN
        answer, then score spread decides what's close enough to include."""
        entity = self._detect_entity(question)
        if entity:
            scoped = [h for h in hits if h.get("state") in (entity, None)]
        else:
            scoped = [h for h in hits if h.get("state") is None]

        if not scoped:
            return []

        top_score = scoped[0]["score"]
        kept = [h for h in scoped if top_score - h["score"] <= _FACT_SPREAD]
        return kept[:2]

    @staticmethod
    def _select_facts(filtered: list[dict]) -> list[dict]:
        """One fact per answer, unless the runner-up is a genuinely different
        topic (a compound question like "how much is it and when is it paid")."""
        if len(filtered) < 2:
            return filtered
        top, second = filtered[0], filtered[1]
        if second.get("topic") != top.get("topic"):
            return [top, second]
        return [top]

    @staticmethod
    def _source_for(hit: dict) -> dict:
        """Provenance for an ANSWER-tier hit: general-facts source, or state records."""
        source = hit.get("source")
        if source is None:
            return dict(_STATE_RECORDS_SOURCE)
        if source.startswith("http"):
            return {"label": "nysc.gov.ng", "url": source, "phone": None}
        return {"label": source, "url": None, "phone": None}

    def _refuse_response(self) -> dict:
        return {
            "answer": FALLBACK,
            "tier": "REFUSE",
            "sources": [dict(_DISTRESS_SOURCE)],
            "followups": [],
        }

    def respond(self, question: str) -> dict:
        q = question.lower()

        # Path 2: health-facility questions → structured query
        if any(kw in q for kw in _HEALTH_KEYWORDS):
            state = next((s for s in self.states if s.lower() in q), None)
            answer = None
            if state:
                answer = self.facilities_summary(state, q)
            if not answer:
                answer = ("Tell me which state (and LGA, if you know it) and I can "
                          "summarize the surveyed health facilities there.")
            return {
                "answer": answer,
                "tier": "ANSWER",
                "sources": [dict(_HEALTH_SOURCE)],
                "followups": [],
            }

        # Path 1: everything else → semantic retrieval + tiered confidence, single pass
        hits = self.retriever.search(question, top_k=8)
        top_score = hits[0]["score"] if hits else 0.0
        tier = self._tier(top_score, bool(hits))

        if tier == "REFUSE":
            return self._refuse_response()

        filtered = self._filter_hits(hits, question)
        if not filtered:
            return self._refuse_response()

        if tier == "ANSWER":
            selected = self._select_facts(filtered)
            facts = [h["text"] for h in selected]
            top_hit = selected[0]
            return {
                "answer": llm.generate_answer(question, facts),
                "tier": "ANSWER",
                "sources": [self._source_for(top_hit)],
                "followups": FOLLOWUPS_BY_TOPIC.get(top_hit.get("topic"), []),
            }

        # PARTIAL: between LOW and HIGH — open by naming what's missing, then
        # give the single top-scoring fact. Never pad with a second, weaker
        # match here — that's an ANSWER-tier-only allowance for compound
        # questions, and a weak second fact does more harm than good.
        top_hit = filtered[0]
        body = top_hit["text"]
        sources = [dict(_GOVNG_SOURCE)]
        entity = self._detect_entity(question)
        if entity and entity in self._secretariat_phones:
            sources.append({
                "label": f"{entity} NYSC secretariat",
                "url": None,
                "phone": self._secretariat_phones[entity],
            })
        return {
            "answer": f"{PARTIAL_PREFIX}\n{body}",
            "tier": "PARTIAL",
            "sources": sources,
            "followups": [],
        }

    def explain(self, question: str) -> dict:
        """Debug view: same retrieval + tier + filter logic as respond(), never disagrees with it."""
        hits = self.retriever.search(question, top_k=8)
        top_score = hits[0]["score"] if hits else 0.0
        tier = self._tier(top_score, bool(hits))
        entity = self._detect_entity(question)
        filtered = self._filter_hits(hits, question)

        def hit_view(h):
            return {"score": round(h["score"], 3), "id": h["id"],
                    "state": h.get("state"), "text": h["text"][:80]}

        return {
            "question": question,
            "entity": entity,
            "tier": tier,
            "top_score": round(top_score, 3),
            "hits": [hit_view(h) for h in hits],
            "filtered_hits": [hit_view(h) for h in filtered],
        }

    @staticmethod
    def _tier(top_score: float, has_hits: bool) -> str:
        if not has_hits or top_score < CONFIDENCE_LOW:
            return "REFUSE"
        if top_score >= CONFIDENCE_HIGH:
            return "ANSWER"
        return "PARTIAL"

    def facilities_summary(self, state: str, q: str) -> str | None:
        from app.facilities import summarize_area
        lgas = self.facilities.loc[self.facilities["state"] == state, "lga"].dropna().unique()
        lga = next((l for l in lgas if l.lower() in q), None)
        return summarize_area(self.facilities, state, lga)
