"""
Tests for Zendesk ticket creation on conversation ended events.
Validates EXTN-476 requirements and demonstrates expected behavior.

Makes real API calls by default, but can be disabled by setting INTEGRATION_TEST=false in your environment.
"""
import pytest
import asyncio
import os
import dotenv
import aiohttp
from unittest.mock import patch, AsyncMock
from datetime import datetime
from app.integrations.zendesk import ZendeskTicketCreator

# Load environment variables from .env file
dotenv.load_dotenv()


@pytest.fixture
def mock_env_enabled():
    """Environment configuration with Zendesk integration enabled."""
    return {
        'ZENDESK_SUBDOMAIN': 'test-sandbox',
        'ZENDESK_EMAIL': 'test@example.com', 
        'ZENDESK_API_TOKEN': 'test-token-123',
        'ZENDESK_AUTO_TICKET_ENABLED': 'true',
        'ZENDESK_AUTO_TICKET_TAG': 'test-demo-tag',
        'ZENDESK_TICKET_PRIORITY': 'high',
        'ZENDESK_TICKET_TYPE': 'incident'
    }


@pytest.fixture  
def mock_env_disabled():
    """Environment configuration with Zendesk integration disabled."""
    return {
        'ZENDESK_SUBDOMAIN': 'test-sandbox',
        'ZENDESK_EMAIL': 'test@example.com',
        'ZENDESK_API_TOKEN': 'test-token-123', 
        'ZENDESK_AUTO_TICKET_ENABLED': 'false'
    }


@pytest.fixture
def mock_env_incomplete():
    """Environment configuration missing required fields."""
    return {
        'ZENDESK_AUTO_TICKET_ENABLED': 'true'
    }


@pytest.fixture
def zendesk_creator_enabled(mock_env_enabled):
    """ZendeskTicketCreator instance with enabled configuration."""
    with patch.dict('os.environ', mock_env_enabled):
        return ZendeskTicketCreator()


@pytest.fixture 
def zendesk_creator_disabled(mock_env_disabled):
    """ZendeskTicketCreator instance with disabled configuration."""
    with patch.dict('os.environ', mock_env_disabled):
        return ZendeskTicketCreator()


@pytest.fixture
def zendesk_creator_incomplete(mock_env_incomplete):
    """ZendeskTicketCreator instance with incomplete configuration."""
    with patch.dict('os.environ', mock_env_incomplete, clear=True):
        return ZendeskTicketCreator()


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        'conversation_id': 'conv-abc123-def456',
        'channel_id': 'channel-xyz789',
        'ended_by': {'role': 'end_user', 'id': 'user-456'},
        'metadata': {'topic': 'billing_inquiry', 'resolved': False, 'user_email': 'customer@example.com'}
    }


@pytest.fixture
def mock_successful_zendesk_response():
    """Mock successful Zendesk API response."""
    return {
        'ticket': {
            'id': 12345,
            'status': 'new',
            'subject': 'Bot Conversation Follow-up - conv-abc1',
            'description': 'Automated ticket...',
            'created_at': '2025-01-01T12:00:00Z'
        }
    }


class TestZendeskTicketCreator:
    """Test suite for ZendeskTicketCreator class."""
    
    def test_configuration_validation_enabled(self, zendesk_creator_enabled):
        """
        GIVEN Zendesk integration is properly configured
        WHEN ZendeskTicketCreator is initialized  
        THEN it should be enabled and configured
        """
        creator = zendesk_creator_enabled
        assert creator.enabled is True
        assert creator.subdomain == 'test-sandbox'
        assert creator.email == 'test@example.com'
        assert creator.token == 'test-token-123'
        assert creator.auto_tag == 'test-demo-tag'
        assert creator.ticket_priority == 'high'
        assert creator.ticket_type == 'incident'
    
    def test_configuration_validation_disabled(self, zendesk_creator_disabled):
        """
        GIVEN Zendesk integration is disabled in config
        WHEN ZendeskTicketCreator is initialized
        THEN it should be disabled but configured
        """
        creator = zendesk_creator_disabled
        assert creator.enabled is False
        assert creator.subdomain == 'test-sandbox'  # Still has config
    
    def test_configuration_validation_incomplete(self, zendesk_creator_incomplete):
        """
        GIVEN Zendesk integration has incomplete configuration
        WHEN ZendeskTicketCreator is initialized
        THEN it should be enabled but missing required fields
        """
        creator = zendesk_creator_incomplete
        assert creator.enabled is True
        assert creator.subdomain is None
        assert creator.email is None
        assert creator.token is None


@pytest.mark.asyncio
class TestTicketCreation:
    """Test suite for ticket creation functionality."""
    
    async def test_successful_ticket_creation(
        self, zendesk_creator_enabled, sample_conversation_data, mock_successful_zendesk_response
    ):
        """
        GIVEN a bot-only conversation ends
        WHEN the conversation is ended by an end user  
        THEN a Zendesk ticket should be created with proper metadata
        """
        # Mock HTTP response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 201
            mock_response.json = AsyncMock(return_value=mock_successful_zendesk_response)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Execute ticket creation
            result = await zendesk_creator_enabled.create_ticket_from_conversation(
                conversation_id=sample_conversation_data['conversation_id'],
                ended_by=sample_conversation_data['ended_by'],
                channel_id=sample_conversation_data['channel_id'],
                metadata=sample_conversation_data['metadata']
            )
            
            # Verify result
            assert result is not None
            assert result['id'] == 12345
            assert result['status'] == 'new'
            assert 'url' in result
            assert 'test-sandbox.zendesk.com/agent/tickets/12345' in result['url']
            
            # Verify API call was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert 'tickets.json' in call_args[0][0]
            
            # Verify request payload
            ticket_payload = call_args[1]['json']['ticket']
            assert 'Bot Conversation Follow-up' in ticket_payload['subject']
            assert 'test-demo-tag' in ticket_payload['tags']
            assert 'bot-conversation' in ticket_payload['tags']
            assert 'automated' in ticket_payload['tags']
            assert ticket_payload['priority'] == 'high'
            assert ticket_payload['type'] == 'incident'
            assert 'billing_inquiry' in ticket_payload['description']
            assert 'user-456' in ticket_payload['description']
    
    async def test_no_ticket_for_disabled_integration(
        self, zendesk_creator_disabled, sample_conversation_data
    ):
        """
        GIVEN Zendesk integration is disabled
        WHEN a conversation ends
        THEN no ticket should be created
        """
        result = await zendesk_creator_disabled.create_ticket_from_conversation(
            conversation_id=sample_conversation_data['conversation_id'],
            ended_by=sample_conversation_data['ended_by']
        )
        
        assert result is None
    
    async def test_no_ticket_for_incomplete_config(
        self, zendesk_creator_incomplete, sample_conversation_data
    ):
        """
        GIVEN Zendesk configuration is incomplete
        WHEN a conversation ends
        THEN no ticket should be created
        """
        result = await zendesk_creator_incomplete.create_ticket_from_conversation(
            conversation_id=sample_conversation_data['conversation_id'],
            ended_by=sample_conversation_data['ended_by']
        )
        
        assert result is None
    
    async def test_no_ticket_for_system_ended_conversation(
        self, zendesk_creator_enabled, sample_conversation_data
    ):
        """
        GIVEN a conversation ended by system timeout
        WHEN the ended_by role is 'system'
        THEN no Zendesk ticket should be created
        """
        system_ended_data = sample_conversation_data.copy()
        system_ended_data['ended_by'] = {'role': 'system', 'id': None}
        
        result = await zendesk_creator_enabled.create_ticket_from_conversation(
            conversation_id=system_ended_data['conversation_id'],
            ended_by=system_ended_data['ended_by']
        )
        
        assert result is None
    
    async def test_no_ticket_for_handoff_ended_conversation(
        self, zendesk_creator_enabled, sample_conversation_data
    ):
        """
        GIVEN a conversation ended by handoff process
        WHEN the ended_by role is 'human_agent'
        THEN no Zendesk ticket should be created
        """
        handoff_ended_data = sample_conversation_data.copy()
        handoff_ended_data['ended_by'] = {'role': 'human_agent', 'id': 'agent-123'}
        
        result = await zendesk_creator_enabled.create_ticket_from_conversation(
            conversation_id=handoff_ended_data['conversation_id'],
            ended_by=handoff_ended_data['ended_by']
        )
        
        assert result is None
    
    async def test_api_error_handling(self, zendesk_creator_enabled, sample_conversation_data):
        """
        GIVEN Zendesk API returns an error
        WHEN attempting to create a ticket
        THEN the error should be handled gracefully
        """
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 400
            mock_response.text = AsyncMock(return_value='Bad Request')
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await zendesk_creator_enabled.create_ticket_from_conversation(
                conversation_id=sample_conversation_data['conversation_id'],
                ended_by=sample_conversation_data['ended_by']
            )
            
            assert result is None
    
    async def test_network_error_handling(self, zendesk_creator_enabled, sample_conversation_data):
        """
        GIVEN network connectivity issues
        WHEN attempting to create a ticket
        THEN the error should be handled gracefully
        """
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = aiohttp.ClientError("Network error")
            
            result = await zendesk_creator_enabled.create_ticket_from_conversation(
                conversation_id=sample_conversation_data['conversation_id'],
                ended_by=sample_conversation_data['ended_by']
            )
            
            assert result is None
    
    async def test_timeout_error_handling(self, zendesk_creator_enabled, sample_conversation_data):
        """
        GIVEN Zendesk API is slow to respond
        WHEN timeout occurs
        THEN the error should be handled gracefully
        """
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.side_effect = asyncio.TimeoutError()
            
            result = await zendesk_creator_enabled.create_ticket_from_conversation(
                conversation_id=sample_conversation_data['conversation_id'],
                ended_by=sample_conversation_data['ended_by']
            )
            
            assert result is None


@pytest.mark.asyncio
class TestHealthCheck:
    """Test suite for Zendesk connectivity validation."""
    
    async def test_health_check_success(self, zendesk_creator_enabled):
        """
        GIVEN Zendesk is properly configured and accessible
        WHEN health check is performed
        THEN it should return True
        """
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await zendesk_creator_enabled.health_check()
            assert result is True
    
    async def test_health_check_auth_error(self, zendesk_creator_enabled):
        """
        GIVEN Zendesk credentials are invalid
        WHEN health check is performed
        THEN it should still return True (connectivity exists)
        """
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 401  # Auth error, but connectivity works
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await zendesk_creator_enabled.health_check()
            assert result is True
    
    async def test_health_check_network_failure(self, zendesk_creator_enabled):
        """
        GIVEN network connectivity issues
        WHEN health check is performed
        THEN it should return False
        """
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_get.side_effect = aiohttp.ClientError("Network error")
            
            result = await zendesk_creator_enabled.health_check()
            assert result is False
    
    async def test_health_check_incomplete_config(self, zendesk_creator_incomplete):
        """
        GIVEN Zendesk configuration is incomplete
        WHEN health check is performed
        THEN it should return False
        """
        result = await zendesk_creator_incomplete.health_check()
        assert result is False


@pytest.mark.asyncio
class TestWebhookIntegration:
    """Test suite for webhook integration with Zendesk."""
    
    async def test_webhook_triggers_ticket_creation(self, sample_conversation_data):
        """
        GIVEN a conversation ended webhook is received
        WHEN the webhook handler processes it
        THEN Zendesk integration should be triggered with correct parameters
        """
        # This test would require importing and testing the webhook handler
        # For now, we test the integration pattern
        
        from app.server.webhooks import EndConversationRequest, EndedBy, EndConversationData
        
        # Create webhook event
        webhook_event = EndConversationRequest(
            type="v1.conversation.ended",
            data=EndConversationData(
                conversation_id=sample_conversation_data['conversation_id'],
                channel_id=sample_conversation_data['channel_id'], 
                ended_by=EndedBy(
                    id=sample_conversation_data['ended_by']['id'],
                    role=sample_conversation_data['ended_by']['role']
                )
            ),
            timestamp=datetime.utcnow()
        )
        
        # Verify webhook event structure
        assert webhook_event.type == "v1.conversation.ended"
        assert webhook_event.data.conversation_id == sample_conversation_data['conversation_id']
        assert webhook_event.data.ended_by.role == 'end_user'
        assert webhook_event.data.ended_by.id == 'user-456'


@pytest.fixture
def integration_test_enabled():
    """Check if integration tests with real API calls are enabled (default: true)."""
    return os.getenv('INTEGRATION_TEST', 'true').lower() == 'true'


@pytest.fixture
def sample_webhook_payload():
    """Sample v1.conversation.ended webhook payload."""
    return {
        "type": "v1.conversation.ended",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": {
            "conversation_id": f"integration-test-{int(datetime.now().timestamp())}",
            "channel_id": "test-channel-456",
            "created_at": "2025-01-15T14:30:00Z",
            "updated_at": "2025-01-15T14:45:00Z",
            "ended_by": {
                "id": "test-user-789",
                "role": "end_user"
            },
            "metadata": {
                "integration_test": True,
                "user_email": "test@example.com",
                "topic": "integration_testing",
                "resolved": False
            }
        }
    }


@pytest.mark.integration
class TestIntegrationWorkflow:
    """Integration tests for complete EXTN-476 workflow."""
    
    def test_webhook_payload_structure(self, sample_webhook_payload):
        """
        GIVEN a v1.conversation.ended webhook payload
        WHEN the payload structure is validated  
        THEN it should contain all required fields
        """
        # Test webhook structure (always runs - no API calls)
        payload = sample_webhook_payload
        
        assert payload["type"] == "v1.conversation.ended"
        assert "timestamp" in payload
        assert "data" in payload
        
        data = payload["data"]
        assert "conversation_id" in data
        assert "channel_id" in data
        assert "ended_by" in data
        assert data["ended_by"]["role"] == "end_user"
        assert "metadata" in data
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_mocked(self, sample_webhook_payload):
        """
        GIVEN a complete webhook payload
        WHEN the webhook is processed (mocked)
        THEN ticket creation should be attempted with correct data
        """
        # This test always runs with mocks - validates workflow logic
        with patch.dict('os.environ', {
            'ZENDESK_AUTO_TICKET_ENABLED': 'true',
            'ZENDESK_SUBDOMAIN': 'test-sandbox',
            'ZENDESK_EMAIL': 'test@example.com',
            'ZENDESK_API_TOKEN': 'test-token'
        }):
            zendesk = ZendeskTicketCreator()
            
            # Mock the API call
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 201
                mock_response.json = AsyncMock(return_value={
                    'ticket': {
                        'id': 99999,
                        'subject': 'Test Ticket',
                        'status': 'new'
                    }
                })
                mock_post.return_value.__aenter__.return_value = mock_response
                
                # Test the complete workflow
                conversation_data = sample_webhook_payload['data']
                ticket = await zendesk.create_ticket_from_conversation(
                    conversation_id=conversation_data['conversation_id'],
                    ended_by=conversation_data['ended_by'],
                    channel_id=conversation_data['channel_id'],
                    metadata=conversation_data['metadata']
                )
                
                assert ticket is not None
                assert ticket['id'] == 99999
                assert 'integration_testing' in mock_post.call_args[1]['json']['ticket']['description']
    
    @pytest.mark.asyncio
    async def test_real_api_integration(self, integration_test_enabled, sample_webhook_payload):
        """
        GIVEN integration tests are enabled and real credentials exist
        WHEN a ticket is created with real API calls
        THEN a real Zendesk ticket should be created
        
        Note: Runs by default - set INTEGRATION_TEST=false to disable real API calls
        """
        if not integration_test_enabled:
            pytest.skip("Integration test skipped - real API calls disabled (INTEGRATION_TEST=false)")
        
        # Verify required environment variables exist
        required_vars = ['ZENDESK_SUBDOMAIN', 'ZENDESK_EMAIL', 'ZENDESK_API_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            pytest.skip(f"Integration test skipped - missing environment variables: {missing_vars}")
        
        print(f"\n🧪 Running REAL API integration test...")
        
        zendesk = ZendeskTicketCreator()
        conversation_data = sample_webhook_payload['data']
        
        # Create real ticket
        ticket = await zendesk.create_ticket_from_conversation(
            conversation_id=conversation_data['conversation_id'],
            ended_by=conversation_data['ended_by'],
            channel_id=conversation_data['channel_id'],
            metadata=conversation_data['metadata']
        )
        
        # Verify real ticket was created
        assert ticket is not None, "Real ticket creation failed"
        assert 'id' in ticket, "Ticket missing ID"
        assert ticket['id'] > 0, "Invalid ticket ID"
        
        print(f"✅ SUCCESS: Real ticket #{ticket['id']} created!")
        print(f"   URL: {ticket.get('url', 'N/A')}")
        
        # Verify ticket contains expected content (first 8 chars of conversation_id)
        assert 'integrat' in ticket['subject'], "Ticket subject should contain integration test identifier"
        

if __name__ == "__main__":
    # Run tests with: python -m pytest tests/test_zendesk_integration.py -v
    pytest.main([__file__, "-v"])
