from typing import Optional

from pydantic import BaseModel


class TargetedSentiment(BaseModel):
    audience: Optional[str]
    sentiment: Optional[str]
