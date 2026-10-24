from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class CallChannel(ABC):
    """
    Abstract Telephony Provider Interface
    Mandate: Telephony: Provider-independent CallChannel interface with actual
    telephone-provider integration.
    """

    @abstractmethod
    async def initiate_outbound_call(
        self,
        to_phone: str,
        session_id: str,
        webhook_url: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Places an outbound telephone call."""
        pass

    @abstractmethod
    async def generate_response(
        self,
        session_id: str,
        prompt_text: str,
        language: str,
        gather_speech: bool = True,
        next_step: Optional[str] = None
    ) -> str:
        """Generates provider-specific call response markup (e.g. TwiML or JSON payload)."""
        pass

    @abstractmethod
    async def transfer_call(self, session_id: str, target_phone: str) -> bool:
        """Transfers call to human clinical team member (CV-07)."""
        pass

    @abstractmethod
    async def terminate_call(self, session_id: str) -> bool:
        """Hangs up or terminates the call session."""
        pass
