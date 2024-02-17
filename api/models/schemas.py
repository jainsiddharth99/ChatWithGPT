import datetime
from pydantic import BaseModel
from helper.utils import get_time
from database.database import samuraiUser
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatDetails:
    samurai_id: str
    chat_prompt: str
    chat_category_id: int
    chat_sub_category_id: int
    chat_id: str = None
    chat_title: str = None
    messages: list = field(default_factory=list)
    created_at: datetime = get_time()
    updated_at: datetime = get_time()


class MessageDetails(BaseModel):
    message_id: int
    message_role: str
    message_type: str
    message_content: str
    message_audio_text: str | None = None
    created_at: str | None = None
