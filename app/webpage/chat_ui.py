from dataclasses import dataclass
from nicegui import ui


@dataclass
class Message:
    role: str
    text: str
    user_id: str | None = None
    name: str | None = None
    avatar: str | None = None

    @property
    def display_name(self):
        if self.role == "ai_agent":
            default_name = "AI Agent"
        elif self.role == "human_agent":
            default_name = "Human Agent"
        else:
            default_name = "End User"

        return f"{self.name or default_name} ({self.user_id or self.role})"


@dataclass
class ChatUI:
    active_end_user_id: str
    active_conversation_id: str

    def __post_init__(self) -> None:
        self._messages: list[Message] = []
        register_chat_ui(self)

    @ui.refreshable
    def notifier_element(self, text: str | None = None):
        if text:
            ui.notification(message=text, position="top", close_button=True, multi_line=True)


    @ui.refreshable
    def message_list_element(self):
        with ui.scroll_area().classes("flex-1") as chat_scroll:
            with ui.column().classes("w-full items-stretch"):
                for m in self._messages:
                    ui.chat_message(text=m.text, sent=(m.user_id == self.active_end_user_id), name=m.display_name, avatar=m.avatar)

        chat_scroll.scroll_to(percent=100)

    def add_message(self, user_id: str | None, role: str, text: str, name: str | None = None, avatar: str | None = None):
        self._messages.append(Message(role, text, user_id, name, avatar))
        self.message_list_element.refresh()

    def send_notification(self, text: str):
        self.notifier_element.refresh(text)


_registered_chats: dict[str, ChatUI] = {}


def register_chat_ui(chat_ui: ChatUI):
    global _registered_chats

    if chat_ui.active_conversation_id in _registered_chats:
        raise ValueError(f"Chat UI already registered for conversation {chat_ui.active_conversation_id}")

    _registered_chats[chat_ui.active_conversation_id] = chat_ui


def get_chat_ui(conversation_id: str) -> ChatUI | None:
    global _registered_chats
    return _registered_chats.get(conversation_id)


def unregister_chat_ui(conversation_id: str):
    global _registered_chats
    if conversation_id in _registered_chats:
        del _registered_chats[conversation_id]
