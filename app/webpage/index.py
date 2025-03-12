import random
from nicegui import ui, APIRouter, app

from app import ada_api
from app.webpage.chat_ui import ChatUI


router = APIRouter(prefix="", tags=["webpage"])


def _generate_names() -> tuple[str, str]:
    first_name = random.choice(["John", "Jane", "Alice", "Bob", "Eve"])
    last_name = random.choice(["Smith", "Johnson", "Williams", "Jones", "Brown"])
    return first_name, last_name


@router.page("/")
async def index():
    async def _send():
        text_value = text_input.value
        chat_ui.add_message(user_id, text_value)
        text_input.value = ""
        await ada_api.send_user_message(conversation_id, user_id, text_value)

    async def _end_chat():
        text_input.value = ""
        text_input._props["placeholder"] = "Conversation has ended"
        text_input.disable()
        end_button.disable()
        await ada_api.end_conversation(conversation_id)

    user_id = app.storage.user.get("end_user_id")
    user_id, conversation_id = await ada_api.start_new_conversation(user_id)
    app.storage.user["end_user_id"] = user_id

    ui.query('.nicegui-content').classes("h-screen flex flex-col w-full")

    chat_ui = ChatUI(user_id, conversation_id)
    chat_ui.notifier_element()
    chat_ui.message_list_element()

    footer = ui.row().classes("h-12 w-full items-stretch")
    with footer:
        text_input = (
            ui.input(placeholder="Type a message...")
            .props("outlined")
            .classes("flex-grow")
            .on("keydown.enter", _send)
        )
        end_button = ui.button("End Chat", on_click=_end_chat, color="red", icon="exit_to_app")
