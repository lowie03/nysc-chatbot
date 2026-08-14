"""Query preprocessing: Pidgin/slang normalization and typo correction."""
import string
from rapidfuzz import fuzz, process

GLOSSARY = {
    "allawee": "allowance",
    "alawee": "allowance",
    "allowee": "allowance",
    "wetin": "what",
    "abeg": "please",
    "dey": "is",
    "corper": "corps member",
    "corpers": "corps members",
    "otondo": "corps member",
}

# Expansions keep the acronym itself alongside the spelled-out form, so the
# query matches corpus text phrased either way.
ACRONYMS = {
    "ppa": "place of primary assignment PPA",
    "cds": "community development service CDS",
    "saed": "skills acquisition and entrepreneurship development SAED",
    "pop": "passing out parade POP",
    "pcm": "prospective corps member PCM",
    "dcc": "distress call centre DCC",
    "nysc": "national youth service corps NYSC",
    "nhia": "national health insurance authority NHIA",
}

_PUNCT = ".,:;'\"()?!"


def normalize(query: str) -> str:
    words = query.lower().split()
    words = [GLOSSARY.get(w, w) for w in words]
    words = [ACRONYMS.get(w.strip(_PUNCT), w) for w in words]
    return " ".join(words)


def build_vocab(docs: list[dict]) -> set[str]:
    vocab = set()
    for doc in docs:
        for word in doc["text"].lower().split():
            word = word.strip(_PUNCT)
            if len(word) > 3:
                vocab.add(word)
    vocab.update(GLOSSARY.values())
    return vocab


def correct_typos(query: str, vocab: set[str]) -> str:
    words = query.split()
    corrected = []
    for word in words:
        if word in vocab or len(word) <= 3:
            corrected.append(word)
            continue
        match = process.extractOne(word, vocab, scorer=fuzz.ratio, score_cutoff=85)
        corrected.append(match[0] if match else word)
    return " ".join(corrected)
