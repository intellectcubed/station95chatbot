"""AWS Lambda handler for GroupMe webhooks via API Gateway."""

import json
import logging
import os
from typing import Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize components (will be reused across Lambda invocations)
roster = None
ai_processor = None
calendar_client = None
message_processor = None
_secrets_cache = None


def _get_secrets():
    """
    Retrieve secrets from AWS Secrets Manager or environment variables.

    Secrets Manager is used in production Lambda, environment variables
    for local development/testing.
    """
    global _secrets_cache

    if _secrets_cache is not None:
        return _secrets_cache

    secret_name = os.environ.get("SECRETS_MANAGER_SECRET_NAME")

    # If Secrets Manager is configured, use it
    if secret_name:
        try:
            import boto3
            from botocore.exceptions import ClientError

            logger.info(f"Fetching secrets from Secrets Manager: {secret_name}")

            session = boto3.session.Session()
            client = session.client(service_name='secretsmanager')

            response = client.get_secret_value(SecretId=secret_name)
            secrets = json.loads(response['SecretString'])

            # Override environment variables with Secrets Manager values
            for key, value in secrets.items():
                if value:  # Only override if value is not empty
                    os.environ[key] = value

            _secrets_cache = secrets
            logger.info("Successfully loaded secrets from Secrets Manager")
            return secrets

        except ClientError as e:
            logger.error(f"Failed to retrieve secrets from Secrets Manager: {e}")
            logger.warning("Falling back to environment variables")
        except Exception as e:
            logger.error(f"Unexpected error retrieving secrets: {e}")
            logger.warning("Falling back to environment variables")

    # Fall back to environment variables (for local development)
    logger.info("Using environment variables for secrets")
    _secrets_cache = {}
    return _secrets_cache


def _initialize_components():
    """Initialize the message processor and its dependencies."""
    global roster, ai_processor, calendar_client, message_processor

    if message_processor is not None:
        return  # Already initialized

    logger.info("Initializing components...")

    # Load secrets (from Secrets Manager or env vars)
    _get_secrets()

    # Import modules AFTER loading secrets so settings picks up the env vars
    # This is critical because these modules import settings at module load time
    from src.station95chatbot.ai_processor import AIProcessor
    from src.station95chatbot.calendar_client import CalendarClient
    from src.station95chatbot.message_processor import MessageProcessor
    from src.station95chatbot.models import GroupMeMessage
    from src.station95chatbot.roster import Roster
    from src.station95chatbot.config import settings

    # Validate AI configuration
    settings.validate_ai_config()

    # Initialize roster
    roster = Roster(settings.roster_file_path)
    logger.info(f"Loaded roster from {settings.roster_file_path}")

    # Initialize AI processor (no parameters - reads from settings)
    ai_processor = AIProcessor()
    logger.info(f"AI processor initialized with provider: {settings.ai_provider}")

    # Initialize calendar client (no parameters - reads from settings)
    calendar_client = CalendarClient()
    logger.info(f"Calendar client initialized: {settings.calendar_service_url}")

    # Initialize message processor
    message_processor = MessageProcessor(
        roster=roster,
        ai_processor=ai_processor,
        calendar_client=calendar_client,
    )

    logger.info("Components initialized successfully")


def _handle_webhook(data: dict[str, Any]) -> dict[str, Any]:
    """
    Process a GroupMe webhook payload.

    GroupMe webhook payload structure:
    {
        "attachments": [],
        "avatar_url": "...",
        "created_at": 1234567890,
        "group_id": "...",
        "id": "...",
        "name": "John Doe",
        "sender_id": "...",
        "sender_type": "user",
        "source_guid": "...",
        "system": false,
        "text": "Message text",
        "user_id": "..."
    }
    """
    logger.info(f"Received webhook: {json.dumps(data)}")

    # Ignore system messages
    if data.get("system", False):
        logger.debug("Ignoring system message")
        return {"status": "ignored", "reason": "system message"}

    # Ignore messages from the bot itself (avoid loops)
    if data.get("sender_type") == "bot":
        logger.debug("Ignoring bot message")
        return {"status": "ignored", "reason": "bot message"}

    # Extract message data
    try:
        from src.station95chatbot.models import GroupMeMessage

        message = GroupMeMessage(
            sender_name=data.get("name", "Unknown"),
            message_text=data.get("text", ""),
            timestamp=data.get("created_at", 0),
            group_id=data.get("group_id", ""),
            message_id=data.get("id", ""),
            sender_id=data.get("sender_id", ""),
            preview=data.get("preview", False),  # Extract preview flag
        )
    except Exception as e:
        logger.error(f"Error parsing webhook data: {e}")
        return {"status": "error", "message": f"Invalid webhook data: {e}"}

    # Process the message
    result = message_processor.process_message(message)

    logger.info(f"Message processing result: {result['reason']}")

    return {
        "status": "processed" if result["processed"] else "ignored",
        "reason": result["reason"],
        "command_sent": result["command_sent"],
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda handler for API Gateway events.

    Args:
        event: API Gateway proxy integration event
        context: Lambda context object

    Returns:
        API Gateway proxy integration response
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Initialize components on cold start
    _initialize_components()

    try:
        # Validate webhook secret if configured
        webhook_secret = os.environ.get("WEBHOOK_SECRET", "")
        if webhook_secret:
            # Check query parameters for secret
            query_params = event.get("queryStringParameters", {}) or {}
            provided_secret = query_params.get("secret", "")

            if provided_secret != webhook_secret:
                logger.warning(f"Invalid webhook secret provided")
                return {
                    "statusCode": 403,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Forbidden"})
                }

            logger.info("Webhook secret validated successfully")

        # Handle GET requests for health checks
        if event.get("requestContext", {}).get("http", {}).get("method") == "GET":
            path = event.get("requestContext", {}).get("http", {}).get("path", "/")

            if path in ["/", "/health"]:
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({
                        "status": "healthy",
                        "service": "Station 95 GroupMe Chatbot Lambda"
                    })
                }

        # Handle POST requests for webhook
        if event.get("requestContext", {}).get("http", {}).get("method") == "POST":
            # Parse the webhook payload from the request body
            body = event.get("body", "{}")

            # Handle base64 encoded bodies (if API Gateway is configured that way)
            if event.get("isBase64Encoded", False):
                import base64
                body = base64.b64decode(body).decode("utf-8")

            try:
                data = json.loads(body)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in request body: {e}")
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON in request body"})
                }

            # Process the webhook
            result = _handle_webhook(data)

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result)
            }

        # Method not allowed
        return {
            "statusCode": 405,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Method not allowed"})
        }

    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
