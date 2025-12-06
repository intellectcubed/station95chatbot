"""GroupMe webhook handler using FastAPI."""

import logging
from typing import Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from .config import settings
from .models import GroupMeMessage
from .message_processor import MessageProcessor

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handles GroupMe webhook callbacks."""

    def __init__(self, message_processor: MessageProcessor):
        """Initialize the webhook handler."""
        self.message_processor = message_processor
        self.bot_id = settings.groupme_bot_id
        self.app = FastAPI(title="Station 95 Chatbot")

        # Register routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        @self.app.get("/")
        async def root():
            """Health check endpoint."""
            return {"status": "ok", "service": "Station 95 GroupMe Chatbot"}

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy"}

        @self.app.post("/webhook")
        async def webhook(request: Request):
            """Handle GroupMe webhook callbacks."""
            try:
                data = await request.json()
                return await self._handle_webhook(data)
            except Exception as e:
                logger.error(f"Error handling webhook: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

    async def _handle_webhook(self, data: dict[str, Any]) -> JSONResponse:
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
        logger.info(f"Received webhook: {data}")

        # Ignore system messages
        if data.get("system", False):
            logger.debug("Ignoring system message")
            return JSONResponse({"status": "ignored", "reason": "system message"})

        # Ignore messages from the bot itself (avoid loops)
        if data.get("sender_type") == "bot":
            logger.debug("Ignoring bot message")
            return JSONResponse({"status": "ignored", "reason": "bot message"})

        # Extract message data
        try:
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
            raise HTTPException(status_code=400, detail=f"Invalid webhook data: {e}")

        # Process the message
        result = self.message_processor.process_message(message)

        logger.info(f"Message processing result: {result['reason']}")

        return JSONResponse(
            {
                "status": "processed" if result["processed"] else "ignored",
                "reason": result["reason"],
                "command_sent": result["command_sent"],
            }
        )

    def run(self, host: str = "0.0.0.0", port: int | None = None) -> None:
        """Run the webhook server."""
        import uvicorn

        port = port or settings.webhook_port
        logger.info(f"Starting webhook server on {host}:{port}")

        uvicorn.run(self.app, host=host, port=port)
