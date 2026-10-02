"""Chat endpoints."""

import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.api.dependencies import get_current_api_key
from app.services.rag_pipeline import RAGPipeline

router = APIRouter()
rag_pipeline = RAGPipeline()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Submit a query and receive a grounded response."""
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                user_id=str(api_key.id),
            )
            db.add(conversation)
            db.commit()
    else:
        conversation = Conversation(
            user_id=str(api_key.id),
        )
        db.add(conversation)
        db.commit()

    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query,
    )
    db.add(user_message)
    db.commit()

    # Run RAG pipeline
    result = rag_pipeline.run(
        query=request.query,
        conversation_history=history,
        top_k=request.top_k,
    )

    # Save assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result.answer,
        sources=result.sources,
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        conversation_id=str(conversation.id),
    )


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Submit a query and receive a streamed response (SSE)."""
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        if not conversation:
            conversation = Conversation(
                id=request.conversation_id,
                user_id=str(api_key.id),
            )
            db.add(conversation)
            db.commit()
    else:
        conversation = Conversation(
            user_id=str(api_key.id),
        )
        db.add(conversation)
        db.commit()

    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    history = [{"role": m.role, "content": m.content} for m in messages]

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.query,
    )
    db.add(user_message)
    db.commit()

    # Stream response
    async def event_generator():
        full_response = ""
        sources = []

        for token in rag_pipeline.run_stream(
            query=request.query,
            conversation_history=history,
            top_k=request.top_k,
        ):
            full_response += token
            yield f"data: {token}\n\n"

        # Save assistant message after streaming completes
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
            sources=sources,
        )
        db.add(assistant_message)
        db.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
