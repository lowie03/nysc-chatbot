"""FastAPI wrapper. Knows nothing about retrieval; bot knows nothing about HTTP."""
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.bot import NYSCBot

app = FastAPI(title="NYSC FAQ Chatbot")
bot = NYSCBot()          # loaded ONCE at startup — model, corpus, 34k rows

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nysc-chatbot-delta.vercel.app/",   # TODO: replace with your real Vercel URL
        "http://localhost:5173",
    ],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
def chat(req: ChatRequest):
    return bot.respond(req.question)


@app.post("/debug")
def debug(req: ChatRequest):
    return bot.explain(req.question)


@app.get("/health")
def health():
    return {"status": "ok", "corpus_size": len(bot.retriever.docs)}