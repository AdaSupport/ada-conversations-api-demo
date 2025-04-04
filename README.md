# Ada Conversations API Demo

This is a demo project providing a minimal implementation of a frontend to interact with an [Ada](https://ada.cx) bot via the Ada Conversations API.

# How to Run this Demo
## Pre-Prodution Requirements

These are things that won't need to be done once everything is GA, but for now they do.

Turn the following LaunchDarkly Feature Flags on for the bot you wish to use: `conversations-api` and `rollout-convo-api-webhooks`

Other pre-production requirements in this README will be highlighted with ⚠️ signs

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

Ada needs to be able to reach the machine this demo is running on via webhook. The simplest way to manage this locally is with something like [ngrok](https://https://ngrok.com/). There are other possible ways of achieiving this but for simplicity we'll assume use of ngrok:

In a new terminal window, start an ngrok http tunnel to port `8080` 

```
ngrok http 8080
```

Take note of the forwarding address. It may be something like `https://1234-56-78-90.ngrok-free.app`

## Bot Configuration

### API Key

Navigate to the Ada dashboard and go to `Platform -> APIs` and create a new API Key. Copy it and save it for later.

### Webhook Configuration

Again in the Ada dashboard, go to `Platform -> Webhooks` and add a new end point. The endpoint URL should be the forwarding address from the `Network Setup` section above *PLUS* `/webhooks/message` appended to it (if using ngrok, then possibly something like `https://1234-56-78-90.ngrok-free.app/webhooks/message`). In the "Subscribe to events" section, make sure you subscribe to all `v1.conversation` events.

Once created, copy and save the `Signing Secret` value.

### Custom Channel Creation

⚠️ This is sub-production at this point. In the future this part will be nicer ⚠️

We need to create a custom channel. At the point of writing the only way to do this against production is via a cURL command:

```
curl -X 'POST' \
  'https://<bot-handle>.ada.support/api/v2/channels/' \
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

Replace `<bot-handle>` with the handle of your bot. And replace `<ada-api-key>` with the API key generated in the section above. Run the command and note the value for the returned `id` field - this is your custom channel ID

Example response:
```
{
"name":"My Custom Channel",
"description":"A custom messaging channel for my AI Agent",
"modality":"messaging",
"status":"active",
"client_id":"5270fcc714fa494c052a1ade",
"external_id":"",
"created_at":"2025-04-04T19:05:43+00:00",
"updated_at":"2025-04-04T19:05:43+00:00",
"id":"61f02d3752d65ca666b44b50",
"type":"custom",
"metadata":{}
}
```

## Putting It All Together

In the base directory of this project, create a `.env` file with the contents:

```
ADA_BASE_URL=your-ada-bot-url
ADA_API_KEY=ada-api-key-you-just-made
ADA_CHANNEL_ID=ada-channel-id-for-custom-channel-you-just-made
WEBHOOK_SECRET=signing-secret-from-endpoint-you-just-added
```

The `ADA_BASE_URL` should be the entire URL to your Ada bot - so something like `https://lovelace.ada.support`

## Running It

Finally, you can run the demo app dashboard by running
```
python run.py
```

and interact with your Ada bot by visiting `http://127.0.0.1:8080` 🎉
