import random
from nicegui import ui, APIRouter, app

from app import ada_api
from app.data.messages import TextContent
from app.webpage.chat_ui import ChatUI


router = APIRouter(prefix="", tags=["webpage"])


def _generate_name() -> str:
    first_name = random.choice(["John", "Jane", "Alice", "Bob", "Eve"])
    last_name = random.choice(["Smith", "Johnson", "Williams", "Jones", "Brown"])
    return f"{first_name} {last_name}"


@router.page("/")
async def index():
    async def _send():
        text_value = text_input.value
        chat_ui.add_message(user_id, "end_user", TextContent(body=text_value), display_name, avatar)
        text_input.value = ""
        await ada_api.send_user_message(conversation_id, user_id, display_name, avatar, text_value)

    async def _end_chat():
        text_input.value = ""
        text_input._props["placeholder"] = "Conversation has ended"
        text_input.disable()
        end_button.disable()
        await ada_api.end_conversation(conversation_id)

    async def _reset():
        app.storage.user.clear()
        ui.navigate.reload()

    user_id = app.storage.user.get("end_user_id")
    display_name = app.storage.user.get("display_name", _generate_name())
    avatar = "https://upload.wikimedia.org/wikipedia/commons/0/09/.hecko_-_Floaty_-_profile_picture.svg"

    user_id, conversation_id = await ada_api.start_new_conversation(user_id)

    app.storage.user["end_user_id"] = user_id
    app.storage.user["display_name"] = display_name
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
        ui.button("Reset", on_click=_reset, color="blue", icon="refresh")
