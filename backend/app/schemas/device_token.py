from typing import Optional
from pydantic import BaseModel, Field


class DeviceTokenRegisterRequest(BaseModel):
    fcm_token: str = Field(..., min_length=10, description="Firebase Cloud Messaging device registration token")
    device_type: Optional[str] = Field("web", description="Device platform: web, android, ios")
    user_agent: Optional[str] = Field(None, max_length=255, description="Client user agent for debugging")


class DeviceTokenUnregisterRequest(BaseModel):
    fcm_token: Optional[str] = Field(None, description="Specific token to deactivate. If omitted, deactivates all active tokens for current patient.")


class NotificationPreferencesUpdateRequest(BaseModel):
    push_enabled: bool = Field(..., description="Enable or disable browser push notifications")


class NotificationPreferencesResponse(BaseModel):
    push_enabled: bool
    has_registered_device: bool
    active_devices_count: int
    registered_at: Optional[str] = None
    last_sent_at: Optional[str] = None
