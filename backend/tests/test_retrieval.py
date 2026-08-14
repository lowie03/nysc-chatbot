"""Questions the bot MUST handle correctly. Add every question it whiffs on."""
import pytest
from app.bot import NYSCBot
from app.loaders import load_states, build_corpus, load_faqs, load_general_facts
from app.preprocess import correct_typos, normalize
from app.retrieval import Retriever, CONFIDENCE_LOW, CONFIDENCE_HIGH


@pytest.fixture(scope="module")
def retriever():
    docs = build_corpus(load_states("data/processed/NYSC.xlsx"))
    docs += load_general_facts("data/general_facts.jsonl")
    docs += load_faqs("data/faqs.jsonl")
    return Retriever(docs, use_cache=False)


@pytest.fixture(scope="module")
def bot():
    return NYSCBot()


def _tier(retriever, question):
    hits = retriever.search(question)
    top_score = hits[0]["score"] if hits else 0.0
    return NYSCBot._tier(top_score, bool(hits)), hits


MUST_ANSWER = [
    ("how much is allawee?", "allowance"),
    ("what is the federal NYSC allowance", "allowance"),
    ("where is the orientation camp in Bayelsa", "camp"),
    ("wetin be camp address for Oyo state?", "camp"),
    ("who is the governor of Rivers state", "governor"),
    # faq_marital_posting_docs (topic "posting") is more complete than the
    # older general-facts version and now legitimately outranks it
    ("what documents does a married woman need to register", "posting"),
    ("how long is orientation camp", "orientation_camp"),
    ("what is CDS", "cds"),
    ("can pregnant women stay in camp", "orientation_camp"),
    ("what number do I call in an emergency", "contact"),
    ("wetin be allawee?", "allowance"),
    ("how much dem dey pay corper?", "allowance"),
    ("where camp dey for Bayelsa?", "camp"),
    ("how mush is the goverment allowanse", "allowance"),
    ("who be govenor of rivers", "governor"),
    ("how do I correct my name on the portal", "corrections"),
    ("what documents do I need to be posted to my husband's state", "posting"),
    ("do medical graduates bring their licence to camp", "orientation_camp"),
    ("how do I collect my exemption certificate", "certificate"),
    ("can I relocate after camp", "relocation"),
    ("What is PPA?", "ppa"),
    ("What is PPA in nysc?", "ppa"),
    ("What is CDS?", "cds"),
    ("What is SAED?", "saed"),
    ("What is POP?", "service_year"),
]

MUST_PARTIAL = [
    "who is the nysc coordinator of imo state?",
]

MUST_REFUSE = [
    "who won the champions league?",
    "write me a poem about love",
    "what is the capital of France",
]


@pytest.mark.parametrize("question,expected_topic", MUST_ANSWER)
def test_answers(retriever, question, expected_topic):
    tier, hits = _tier(retriever, question)
    assert tier == "ANSWER", f"{question!r} landed in {tier} (top={hits[0]['score']:.3f})"
    assert hits[0]["topic"] == expected_topic, (
        f"{question!r} matched {hits[0]['id']} ({hits[0]['score']:.3f})"
    )


@pytest.mark.parametrize("question", MUST_PARTIAL)
def test_partials(retriever, question):
    tier, hits = _tier(retriever, question)
    top_score = hits[0]["score"] if hits else 0.0
    assert tier == "PARTIAL", f"{question!r} landed in {tier} (top={top_score:.3f})"


@pytest.mark.parametrize("question", MUST_REFUSE)
def test_refusals(retriever, question):
    tier, hits = _tier(retriever, question)
    top_score = hits[0]["score"] if hits else 0.0
    assert tier == "REFUSE", f"{question!r} landed in {tier} (top={top_score:.3f})"


def test_thresholds_are_ordered():
    assert 0.0 <= CONFIDENCE_LOW < CONFIDENCE_HIGH <= 1.0


def test_normalize_translates_pidgin():
    # "allawee" keeps its trailing "?" glued on, so it doesn't exact-match the
    # GLOSSARY key — normalize() only does whole-word lookups, no punctuation
    # stripping. That gap is covered separately by the corpus content itself.
    assert normalize("wetin be allawee?") == "what be allawee?"


def test_correct_typos_fixes_known_word_but_skips_short_words():
    vocab = {"government"}
    assert correct_typos("goverment", vocab) == "government"
    assert correct_typos("cat", vocab) == "cat"


def test_normalize_expands_acronyms():
    # The acronym expansion keeps the acronym itself alongside the spelled-out
    # form, and is punctuation-tolerant so "PPA?" still matches the "ppa" key.
    assert normalize("What is PPA?") == "what is place of primary assignment PPA"
    assert normalize("what is pop") == "what is passing out parade POP"


def test_partial_response_always_has_govng_source(bot):
    resp = bot.respond("who is the nysc coordinator of imo state?")
    assert resp["tier"] == "PARTIAL"
    assert any(s.get("url") == "https://www.nysc.gov.ng/" for s in resp["sources"])


def test_refuse_response_has_distress_phone(bot):
    resp = bot.respond("who won the champions league?")
    assert resp["tier"] == "REFUSE"
    assert any(s.get("phone") == "6972" for s in resp["sources"])


def test_answer_response_has_nonempty_sources(bot):
    resp = bot.respond("how much is allawee?")
    assert resp["tier"] == "ANSWER"
    assert len(resp["sources"]) > 0


def test_partial_response_never_has_two_facts(bot):
    """PARTIAL must show at most one fact — the compound-question exception
    (second fact if within spread and a different topic) is ANSWER-only."""
    resp = bot.respond("who is the nysc coordinator of imo state?")
    assert resp["tier"] == "PARTIAL"
    body = resp["answer"].split("\n", 1)[1]
    assert not body.startswith("- "), "PARTIAL answer looks bulleted (more than one fact)"
    assert "\n- " not in resp["answer"], "PARTIAL answer contains a bulleted second fact"


MUST_BE_SINGLE_ENTITY = [
    "where is the orientation camp in Bayelsa",
    "where is the NYSC secretariat in Oyo state?",
    "who is the governor of Rivers state",
]

MUST_EXCLUDE_ALL_ENTITIES = [
    "how long is orientation camp",     # duration question, names no state
    "what is CDS",                      # definition question, names no state
]


@pytest.mark.parametrize("question", MUST_BE_SINGLE_ENTITY)
def test_entity_question_returns_single_entity(bot, question):
    """A question naming one state must never mix in a sibling state's fact.

    This assertion is structural (at most one non-null state among the
    survivors) rather than pinned to a specific state, so it holds for
    whichever entity the question happens to name.
    """
    hits = bot.retriever.search(question, top_k=8)
    filtered = bot._filter_hits(hits, question)
    assert filtered, f"{question!r} returned no hits after filtering"
    entities = {h["state"] for h in filtered if h.get("state") is not None}
    assert len(entities) <= 1, f"{question!r} mixed entities: {entities}"


@pytest.mark.parametrize("question", MUST_EXCLUDE_ALL_ENTITIES)
def test_general_question_excludes_entity_scoped_facts(bot, question):
    """A question naming no state must never be answered by an entity-scoped fact."""
    hits = bot.retriever.search(question, top_k=8)
    filtered = bot._filter_hits(hits, question)
    entity_hits = [h["id"] for h in filtered if h.get("state") is not None]
    assert not entity_hits, f"{question!r} pulled in entity-scoped facts: {entity_hits}"


FAQ_QUESTIONS = [
    "how do I correct my name on the portal",
    "what documents do I need to be posted to my husband's state",
    "do medical graduates bring their licence to camp",
    "how do I collect my exemption certificate",
    "can I relocate after camp",
]


@pytest.mark.parametrize("question", FAQ_QUESTIONS)
def test_faq_response_never_leaks_embed_text(bot, question):
    """respond() must surface a doc's answer (text), never its embed_text
    (question + text glued together for retrieval only)."""
    resp = bot.respond(question)
    embed_texts = [d["embed_text"] for d in bot.retriever.docs if "embed_text" in d]
    assert not any(et in resp["answer"] for et in embed_texts), (
        f"{question!r} leaked an embed_text value into the answer"
    )


def test_load_faqs_sets_state_none_and_embed_text():
    docs = load_faqs("data/faqs.jsonl")
    assert docs, "no FAQ docs loaded"
    for doc in docs:
        assert doc["state"] is None
        assert doc["embed_text"]
