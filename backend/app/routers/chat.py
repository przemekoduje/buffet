from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.services.chat_agent import ChatAgent
from app.knowledge import get_topics_list, get_topic_by_id, get_full_knowledge_document

router = APIRouter(prefix="/api/chat", tags=["AI Chat Advisor"])

class ChatMessage(BaseModel):
    role: str # "user" | "assistant" | "system"
    content: str

    class Config:
        extra = "ignore"

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context_ticker: Optional[str] = None
    custom_data: Optional[str] = None

@router.post("")
async def send_chat_message(payload: ChatRequest, db: Session = Depends(get_db)):
    if not payload.messages:
        raise HTTPException(status_code=400, detail="Brak wiadomości w zapytaniu")

    msgs = [{"role": m.role, "content": m.content} for m in payload.messages]
    result = await ChatAgent.process_chat(
        messages=msgs,
        context_ticker=payload.context_ticker,
        custom_data=payload.custom_data,
        db=db
    )
    return result

@router.get("/suggestions")
def get_chat_suggestions():
    return {
        "suggestions": [
            {
                "label": "Przeanalizuj fundamentalnie Apple (AAPL)",
                "prompt": "Przeanalizuj dla mnie spółkę Apple (AAPL). Jak wypada jej fosa ekonomiczna i czy obecna cena daje margines bezpieczeństwa?",
                "icon": "sparkles"
            },
            {
                "label": "Czy Berkshire Hathaway (BRK.B) ma margines?",
                "prompt": "Jak wyceniane jest obecnie Berkshire Hathaway (BRK.B) i czy warto je teraz dokupić do portfela?",
                "icon": "shield"
            },
            {
                "label": "Prześwietl stan mojego portfela i ryzyko",
                "prompt": "Prześwietl mój obecny portfel inwestycyjny. Czy przestrzegam Reguły nr 1 i jak wypadam względem indeksu S&P 500?",
                "icon": "wallet"
            },
            {
                "label": "Pokaż najlepsze okazje ze Screenera",
                "prompt": "Jakie spółki mają aktualnie najwyższy Buffett Score i największe niedowartościowanie w Screenerze?",
                "icon": "compass"
            },
            {
                "label": "Jak liczycie wycenę DCF i Owner Earnings?",
                "prompt": "Wytłumacz mi szczegółowo, jak aplikacja wylicza wartość wewnętrzną (Intrinsic Value) i czym różni się Owner Earnings od zwykłego zysku netto?",
                "icon": "help"
            }
        ]
    }

@router.get("/knowledge")
def list_knowledge_topics():
    """Zwraca spis treści i tematy z Banku Wiedzy aplikacji BUFFET."""
    return {
        "topics": get_topics_list(),
        "total": len(get_topics_list())
    }

@router.get("/knowledge/{topic_id}")
def get_knowledge_topic(topic_id: str):
    """Zwraca pełny artykuł merytoryczny z Banku Wiedzy dla wybranego zagadnienia."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Nie znaleziono tematu w Banku Wiedzy")
    return topic

