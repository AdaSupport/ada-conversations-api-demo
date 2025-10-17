import asyncio
from datetime import datetime
import os
from typing import Any, Literal, cast
import dotenv
from fastapi import HTTPException, Request
from nicegui import APIRouter
from pydantic import BaseModel
import svix

from app.data.messages import LinkContent, MessageContent, TextContent
from app.webpage.chat_ui import get_chat_ui
from app.integrations.zendesk import ZendeskTicketCreator

dotenv.load_dotenv()
WEBHOOK_SECRET = os.environ["WEBHOOK_SECRET"]


class PostMessageAuthor(BaseModel):
    display_name: str | None
    role: str
    avatar: str | None
    id: str | None


class PostMessageData(BaseModel):
    message_id: str
    conversation_id: str
    channel_id: str
    created_at: datetime
    author: PostMessageAuthor
    content: TextContent | LinkContent


class PostMessageRequest(BaseModel):
    type: Literal["v1.conversation.message"]
    data: PostMessageData
    timestamp: datetime


class EndedBy(BaseModel):
    id: str | None
    role: str


class EndConversationData(BaseModel):
    conversation_id: str
    channel_id: str
    ended_by: EndedBy


class EndConversationRequest(BaseModel):
    type: Literal["v1.conversation.ended"]
    data: EndConversationData
    timestamp: datetime


class ConversationCreatedData(BaseModel):
    conversation_id: str
    channel_id: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class ConversationCreatedRequest(BaseModel):
    type: Literal["v1.conversation.created"]
    data: ConversationCreatedData
    timestamp: datetime


class GenericEventRequest(BaseModel):
    type: str
    data: dict[str, Any]
    timestamp: datetime

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Initialize Zendesk integration for demo
zendesk = ZendeskTicketCreator()

_global_msg_queue: list[PostMessageRequest] = []
_global_batch_task: asyncio.Task | None = None
_global_batch_lock = asyncio.Lock()


@router.post("/message", status_code=204)
async def post_message(msg: PostMessageRequest | EndConversationRequest | ConversationCreatedRequest | GenericEventRequest, request: Request):
    print(f"\033[94mReceived webhook: {msg.model_dump_json()}\033[0m")

    headers = request.headers
    payload = await request.body()

    try:
        # Alternatively you can follow these docs for manual signature verification: https://docs.svix.com/receiving/verifying-payloads/how-manual
        webhook = svix.Webhook(WEBHOOK_SECRET)
        webhook.verify(payload, cast(dict[str, str], headers))
    except svix.WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail="Bad Request") from e

    if isinstance(msg, PostMessageRequest):
        await push_message_to_queue(msg)
    elif isinstance(msg, EndConversationRequest):
        chat_ui = get_chat_ui(msg.data.conversation_id)
        if chat_ui:
            chat_ui.disable_chat_inputs()

        print(f"\033[95m🎫 Processing conversation ended event for {msg.data.conversation_id[:8]}...\033[0m")
        
        ticket = await zendesk.create_ticket_from_conversation(
            conversation_id=msg.data.conversation_id,
            ended_by=msg.data.ended_by.model_dump(),
            channel_id=msg.data.channel_id,
            metadata=getattr(msg.data, 'metadata', None)
        )
        
        if ticket and chat_ui:
            # Notify user that follow-up ticket was created
            ticket_url = ticket.get('url', '#')
            if ticket_url != '#':
                chat_ui.send_notification(
                    f"📋 A follow-up ticket #{ticket['id']} has been created for your conversation. "
                    f"View: {ticket_url}"
                )
            else:
                chat_ui.send_notification(
                    f"📋 A follow-up ticket #{ticket['id']} has been created for your conversation."
                )
            print(f"\033[92m✨ Demo success: User notified of ticket #{ticket['id']}\033[0m")
        elif zendesk.enabled and chat_ui:
            # If Zendesk is enabled but failed, still notify user
            chat_ui.send_notification(
                "📋 A follow-up ticket creation was attempted but failed. Please contact support if needed."
            )
    elif isinstance(msg, ConversationCreatedRequest):
        print(f"\033[96m🎬 Processing conversation created event for {msg.data.conversation_id[:8]}...\033[0m")
        
        # Log the conversation creation for debugging
        print(f"   Conversation ID: {msg.data.conversation_id}")
        print(f"   Channel ID: {msg.data.channel_id}")
        print(f"   Created At: {msg.data.created_at}")
        if msg.data.metadata:
            print(f"   Metadata: {msg.data.metadata}")
        
        # The conversation created event doesn't need special UI handling in this demo
        # The AI agent greeting will come through as a separate v1.conversation.message event
        print(f"\033[92m✅ Conversation created event processed successfully\033[0m")
    else:
        print(f"\033[90mWebhook failed to parse or received unsupported type: {msg.type}\033[0m")


async def push_message_to_queue(msg: PostMessageRequest):
    """Batch messages in a queue to be processed after a delay to account for unordered messages"""
    global _global_batch_lock

    async with _global_batch_lock:
        global _global_msg_queue, _global_batch_task
        print("Pushing message to queue")
        _global_msg_queue.append(msg)

        if _global_batch_task is not None:
            print("Rescheduling batch task")
            _global_batch_task.cancel()
        else:
            print("Scheduling new batch task")

        _global_batch_task = asyncio.create_task(batch_process_messages())


async def batch_process_messages():
    """Process all messages in the queue after a delay"""
    global _global_batch_lock

    await asyncio.sleep(2)

    async with _global_batch_lock:
        global _global_msg_queue, _global_batch_task
        messages = _global_msg_queue
        _global_msg_queue = []
        _global_batch_task = None

    print("Processing batched messages")
    messages.sort(key=lambda m: m.timestamp)
    for msg in messages:
        push_message_to_chat(
            msg.data.conversation_id,
            msg.data.author.id,
            msg.data.author.role,
            msg.data.content,
            msg.data.author.display_name,
            msg.data.author.avatar,
        )


def push_message_to_chat(conversation_id: str, user_id: str | None, role: str, content: MessageContent, display_name: str | None = None, avatar: str | None = None):
    """Convert a message from Ada's webhook to one that is displayed in the chat UI"""

    chat_ui = get_chat_ui(conversation_id)
    if not chat_ui or user_id == chat_ui.active_end_user_id:
        return

    if content.type == "presence":
        chat_ui.send_notification(content.body)
    else:
        chat_ui.add_message(user_id, role, content, display_name, avatar)
