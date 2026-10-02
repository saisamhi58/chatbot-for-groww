"""Conversation management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import Conversation, Message, get_db
from app.models.schemas import ConversationResponse, MessageResponse
from app.api.dependencies import get_current_api_key

router = APIRouter()


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Get conversation history."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise ValueError("Conversation not found")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()

    return ConversationResponse(
        conversation_id=str(conversation.id),
        messages=[
            MessageResponse(
                role=m.role,
                content=m.content,
                sources=m.sources or [],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    api_key=Depends(get_current_api_key),
):
    """Delete a conversation and all its messages."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise ValueError("Conversation not found")

    db.delete(conversation)
    db.commit()

    return {"message": "Conversation deleted successfully"}
