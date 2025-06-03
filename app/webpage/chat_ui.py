from dataclasses import dataclass

from nicegui import ui

from app.data.messages import LinkContent, MessageContent, TextContent


@dataclass
class Message:
    role: str
    content: MessageContent
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
    _text_input: ui.input | None = None
    _end_button: ui.button | None = None
    _reset_button: ui.button | None = None

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
                    bubble_text = m.content.body if isinstance(m.content, TextContent) else []

                    chat_msg = ui.chat_message(text=bubble_text, sent=(m.user_id == self.active_end_user_id), name=m.display_name, avatar=m.avatar)
                    if isinstance(m.content, LinkContent):
                        with chat_msg:
                            ui.button(m.content.link_text or "Click this link", on_click=lambda: ui.navigate.to(m.content.url, new_tab=True))

                    if m.role == "ai_agent":
                        chat_msg.props("bg-color=green-3")
                    elif m.role == "human_agent":
                        chat_msg.props("bg-color=blue-3")

        chat_scroll.scroll_to(percent=100)

    @property
    def text_input(self) -> ui.input:
        if self._text_input is None:
            self._text_input = ui.input(placeholder="Type a message...").props("outlined").classes("flex-grow")
        return self._text_input

    @property
    def end_button(self) -> ui.button:
        if self._end_button is None:
            self._end_button = ui.button("End Chat", color="red", icon="exit_to_app")
        return self._end_button

    @property
    def reset_button(self) -> ui.button:
        if self._reset_button is None:
            self._reset_button = ui.button("Reset", color="blue", icon="refresh")
        return self._reset_button

    def chat_footer(self) -> ui.row:
        footer = ui.row().classes("h-12 w-full items-stretch")
        with footer:
            self.text_input
            self.end_button
            self.reset_button
        return footer

    def disable_chat_inputs(self):
        self.text_input.value = ""
        self.text_input._props["placeholder"] = "Conversation has ended"
        self.text_input.disable()
        self.end_button.disable()

    def add_message(self, user_id: str | None, role: str, content: MessageContent, name: str | None = None, avatar: str | None = None):
        self._messages.append(Message(role, content, user_id, name, avatar))
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
