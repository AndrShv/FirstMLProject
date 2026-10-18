from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from workspace.entity.enums import Subscriptions, SubscriptionStatus


class SubscriptionInfoResponse(BaseModel):
    subscription: Subscriptions
    subscription_status: SubscriptionStatus
    subscription_expires_at: Optional[datetime]
    is_active: bool
