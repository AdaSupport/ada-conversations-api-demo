"""
Zendesk ticket creation integration for conversation ended events.
Demonstrates immediate action on bot-only conversation completion.
"""
import os
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime

class ZendeskTicketCreator:
    """
    Creates Zendesk tickets when Ada conversations end.
    """
    
    def __init__(self):
        self.subdomain = os.getenv('ZENDESK_SUBDOMAIN')
        self.email = os.getenv('ZENDESK_EMAIL') 
        self.token = os.getenv('ZENDESK_API_TOKEN')
        self.enabled = os.getenv('ZENDESK_AUTO_TICKET_ENABLED', 'false').lower() == 'true'
        self.auto_tag = os.getenv('ZENDESK_AUTO_TICKET_TAG', 'ada-bot-conversation')
        self.ticket_priority = os.getenv('ZENDESK_TICKET_PRIORITY', 'normal')
        self.ticket_type = os.getenv('ZENDESK_TICKET_TYPE', 'question')
        
        # Validate configuration on initialization
        self._log_configuration_status()
        
    def _log_configuration_status(self) -> None:
        """Log configuration status for demo visibility."""
        if not self.enabled:
            print("\033[93m🔧 Zendesk integration disabled (ZENDESK_AUTO_TICKET_ENABLED=false)\033[0m")
            return
            
        missing_configs = []
        if not self.subdomain: missing_configs.append('ZENDESK_SUBDOMAIN')
        if not self.email: missing_configs.append('ZENDESK_EMAIL')
        if not self.token: missing_configs.append('ZENDESK_API_TOKEN')
        
        if missing_configs:
            print(f"\033[91m❌ Zendesk integration misconfigured. Missing: {', '.join(missing_configs)}\033[0m")
        else:
            print(f"\033[92m✅ Zendesk integration configured for {self.subdomain}.zendesk.com\033[0m")
        
    async def create_ticket_from_conversation(
        self, 
        conversation_id: str,
        ended_by: Dict[str, Any],
        channel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Zendesk ticket when a bot-only conversation ends.
        """
        if not self.enabled:
            print("\033[90m📋 Zendesk ticket creation disabled\033[0m")
            return None
            
        if not self._is_configured():
            print("\033[91m❌ Cannot create ticket - Zendesk not configured\033[0m")
            return None
            
        # Only create tickets for bot-only conversations ended by users
        if ended_by.get('role') != 'end_user':
            print(f"\033[90m📋 Skipping ticket creation - ended by {ended_by.get('role')}\033[0m")
            return None
            
        print(f"\033[96m🎫 Creating Zendesk ticket for conversation {conversation_id[:8]}...\033[0m")
        
        try:
            ticket_data = self._build_ticket_payload(conversation_id, ended_by, channel_id, metadata)
            result = await self._send_ticket_to_zendesk(ticket_data)
            
            if result:
                ticket_url = self._generate_ticket_url(result['id'])
                print(f"\033[92m✅ Created Zendesk ticket #{result['id']}: {ticket_url}\033[0m")
                return {**result, 'url': ticket_url}
            else:
                print("\033[91m❌ Failed to create Zendesk ticket\033[0m")
                return None
                
        except Exception as e:
            print(f"\033[91m❌ Error creating Zendesk ticket: {str(e)}\033[0m")
            return None
            
    def _is_configured(self) -> bool:
        """Check if all required configuration is present."""
        return all([self.subdomain, self.email, self.token])
        
    def _build_ticket_payload(
        self, 
        conversation_id: str, 
        ended_by: Dict[str, Any],
        channel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict:
        """Build Zendesk ticket payload from conversation data."""
        # Extract user info if available
        user_id = ended_by.get('id', 'unknown')
        
        ticket = {
            "subject": f"Bot Conversation Follow-up - {conversation_id[:8]}",
            "description": self._generate_description(conversation_id, ended_by, channel_id, metadata),
            "tags": [self.auto_tag, "bot-conversation", "automated"],
            "priority": self.ticket_priority,
            "type": self.ticket_type,
            "status": "new"
        }
        
        # Add custom fields if available
        custom_fields = []
        if conversation_id:
            custom_fields.append({"id": "ada_conversation_id", "value": conversation_id})
        if channel_id:
            custom_fields.append({"id": "ada_channel_id", "value": channel_id})
        if user_id != 'unknown':
            custom_fields.append({"id": "ada_user_id", "value": user_id})
            
        if custom_fields:
            ticket["custom_fields"] = custom_fields
            
        return {"ticket": ticket}
        
    def _generate_description(
        self, 
        conversation_id: str, 
        ended_by: Dict[str, Any],
        channel_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate comprehensive ticket description."""
        lines = [
            "🤖 Automated ticket created from ended bot conversation",
            "",
            "**Conversation Details:**",
            f"• Conversation ID: {conversation_id}",
            f"• Channel ID: {channel_id or 'N/A'}",
            f"• Ended by: {ended_by.get('role', 'unknown')} ({ended_by.get('id', 'N/A')})",
            f"• Ended at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        ]
        
        if metadata and isinstance(metadata, dict):
            lines.extend([
                "",
                "**Conversation Metadata:**"
            ])
            for key, value in metadata.items():
                lines.append(f"• {key}: {value}")
                
        lines.extend([
            "",
            "---",
            "**Next Steps:**",
            "• Review the conversation for any unresolved issues",
            "• Determine if follow-up with the customer is needed", 
            "• Update ticket status once reviewed",
            "",
            "*This ticket demonstrates immediate action on conversation end events,*",
            "*eliminating the need to wait for 24-hour timeout.*"
        ])
        
        return "\n".join(lines)
        
    def _generate_ticket_url(self, ticket_id: int) -> str:
        """Generate direct URL to the created ticket."""
        return f"https://{self.subdomain}.zendesk.com/agent/tickets/{ticket_id}"
        
    async def _send_ticket_to_zendesk(self, ticket_data: Dict) -> Optional[Dict[str, Any]]:
        """Send ticket creation request to Zendesk API."""
        url = f"https://{self.subdomain}.zendesk.com/api/v2/tickets.json"
        # Zendesk API v2 authentication: email/token as username, API token as password
        auth = aiohttp.BasicAuth(f"{self.email}/token", self.token)
        
        timeout = aiohttp.ClientTimeout(total=10)  # 10 second timeout
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json=ticket_data,
                    auth=auth,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Ada-Conversations-API-Demo/1.0"
                    }
                ) as response:
                    if response.status == 201:
                        result = await response.json()
                        return result['ticket']
                    else:
                        error_text = await response.text()
                        print(f"\033[91mZendesk API error {response.status}: {error_text}\033[0m")
                        return None
                        
        except aiohttp.ClientError as e:
            print(f"\033[91mNetwork error connecting to Zendesk: {str(e)}\033[0m")
            return None
        except asyncio.TimeoutError:
            print("\033[91mTimeout connecting to Zendesk API\033[0m")
            return None
        except Exception as e:
            print(f"\033[91mUnexpected error: {str(e)}\033[0m")
            return None
            
    async def health_check(self) -> bool:
        """
        Test Zendesk connectivity for demo setup validation.
        """
        if not self._is_configured():
            return False
            
        # Use a simpler endpoint for health check - just test basic auth
        url = f"https://{self.subdomain}.zendesk.com/api/v2/users/me.json"
        auth = aiohttp.BasicAuth(f"{self.email}/token", self.token)
        timeout = aiohttp.ClientTimeout(total=5)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, auth=auth) as response:
                    return response.status in [200, 401, 403]  # Any auth response means connectivity works
        except:
            return False
