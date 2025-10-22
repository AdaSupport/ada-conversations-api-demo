import json
import os
import ssl
import aiohttp
import dotenv


dotenv.load_dotenv()
ADA_BASE_URL = os.environ["ADA_BASE_URL"]
ADA_API_KEY = os.environ["ADA_API_KEY"]
ADA_CHANNEL_ID = os.environ["ADA_CHANNEL_ID"]


def _colorize(status_code: int, text: str) -> str:
    return (
        (
            "\033[92mSuccess Response: "
            if status_code < 300
            else "\033[91mError Response"
        )
        + text
        + "\033[0m"
    )


async def send_user_message(
    conversation_id: str, user_id: str, display_name: str, avatar: str, text: str
):
    """Send an end user message to Ada"""

    print("Sending message...")
    # Create SSL context that doesn't verify certificates (for development)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            f"{ADA_BASE_URL}/api/v2/conversations/{conversation_id}/messages",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            json={
                "author": {
                    "role": "end_user",
                    "display_name": display_name,
                    "id": user_id,
                    "avatar": avatar,
                },
                "content": {"type": "text", "body": text},
            },
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()


async def start_new_conversation(user_id: str | None = None):
    """Start a new conversation with Ada"""

    print("Starting conversation...")
    request_body = {"channel_id": ADA_CHANNEL_ID}
    if user_id:
        print("...with end_user_id....")
        request_body["end_user_id"] = user_id

    # Create SSL context that doesn't verify certificates (for development)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            f"{ADA_BASE_URL}/api/v2/conversations",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
            json=request_body,
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()

            return body["end_user_id"], body["id"]


async def end_conversation(conversation_id: str):
    """End a conversation with Ada"""

    print("Ending conversation...")
    # Create SSL context that doesn't verify certificates (for development)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(
            f"{ADA_BASE_URL}/api/v2/conversations/{conversation_id}/end",
            headers={"Authorization": f"Bearer {ADA_API_KEY}"},
        ) as response:
            body = await response.json()
            print(_colorize(response.status, json.dumps(body)))

            response.raise_for_status()


