# Ada Conversations API Demo

This is a demo project providing a minimal implementation of a frontend to interact with an [Ada](https://ada.cx) AI Agent via the Ada Conversations API.

# How to Run this Demo

## Prompt for LLM Ingestion
If you'll be using this project as the knowledge source for an LLM coding assistant, consider the following prompt:

> Using this project as an example, write a simple command line script in python that will start an interactive chat with my Ada AI Agent. To receive messages from the Ada AI Agent listen on port 8080 to the path `/webhooks/message`. Messages that come from in from the Ada AI Agent should be represented on the command line chat as from 'AI Agent'. Suppress all other non-critical log messages, only showing the chat dialog between the user and the Ada AI Agent.

## Environment Setup

Clone this repo and `cd` into it.

If using a virtual env, create one and activate it:

```
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:
```
pip install -e .
```

## Network Setup

Ada needs to be able to reach the machine that this demo is running on via webhook. The simplest way to manage this locally is with something like [ngrok](https://https://ngrok.com/). There are other possible ways of achieving this but for simplicity we'll assume use of ngrok:

In a new terminal window, start an ngrok http tunnel to port `8080` 

```
ngrok http 8080
```

Take note of the forwarding address. It may be something like `https://1234-56-78-90.ngrok-free.app`

## Bot Configuration

### API Key

Navigate to the Ada dashboard and go to `Platform -> APIs` and create a new API Key. Copy it and save it for later.

### Webhook Configuration

Again in the Ada dashboard, go to `Platform -> Webhooks` and add a new endpoint. The endpoint URL should be the forwarding address from the `Network Setup` section above *PLUS* `/webhooks/message` appended to it (if using ngrok, then possibly something like `https://1234-56-78-90.ngrok-free.app/webhooks/message`). In the "Subscribe to events" section, make sure you subscribe to all `v1.conversation` events.

Once created, copy and save the `Signing Secret` value.

### Custom Channel Creation

We need to create a custom channel. To create a custom channel in production, we can use the following cURL command:

```
curl -X 'POST' \
  'https://<ai-agent-handle>.ada.support/api/v2/channels/' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer <ada-api-key>' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "My Custom Channel",
  "description": "A custom messaging channel for my AI Agent",
  "modality": "messaging",
  "status": "active"
}'
```

Replace `<ai-agent-handle>` with the handle of your AI Agent, and `<ada-api-key>` with the API key generated in the section above. Run the command and note the value for the returned `id` field - this is your custom channel ID

## Putting It All Together

In the base directory of this project, create a `.env` file with the contents:

```
ADA_BASE_URL=your-ada-ai-agent-url
ADA_API_KEY=ada-api-key-you-just-made
ADA_CHANNEL_ID=ada-channel-id-for-custom-channel-you-just-made
WEBHOOK_SECRET=signing-secret-from-endpoint-you-just-added
```

The `ADA_BASE_URL` should be the entire URL to your Ada AI Agent - so something like `https://lovelace.ada.support`

## Zendesk Integration (EXTN-476 Demo)

This demo includes a Zendesk integration that automatically creates tickets when bot conversations end, demonstrating immediate customer follow-up instead of needing to waiting for 24-hour timeout.

### Configuration

Add these environment variables to your `.env` file to enable Zendesk integration:

```bash
# Zendesk Integration (Optional)
ZENDESK_AUTO_TICKET_ENABLED=true
ZENDESK_SUBDOMAIN=your-zendesk-subdomain  
ZENDESK_EMAIL=admin@yourcompany.com
ZENDESK_API_TOKEN=your-zendesk-api-token
ZENDESK_AUTO_TICKET_TAG=ada-bot-conversation
```

### Demo Flow
1. Customer starts conversation → chats with bot → clicks "End Chat" 
2. Ada fires `v1.conversation.ended` webhook → Demo creates Zendesk ticket
3. Customer sees notification: "Follow-up ticket #12345 created"
4. Agent sees new ticket in Zendesk with correct conversation context

## Running It

Finally, you can run the demo app dashboard by running
```
python run.py
```

and interact with your Ada AI Agent by visiting `http://127.0.0.1:8080` 🎉


> [!IMPORTANT]
> This code is for example use only, and modifications may be needed to run this code. Additionally, pull requests and/or issues for this repository will not be monitored.
