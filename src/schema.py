from typing import List, Literal
from pydantic import BaseModel

class Tag(BaseModel):
    sentiment: Literal["positive","negative","neutral","mixed"]
    emotion: Literal["craving","hyped","disappointed","angry","neutral","other"]
    aspects: List[Literal["taste_quality","price_value","ambiance_vibe","service_speed","menu_hype","other","none"]]
    intent: Literal["ordering_now","recommendation","complaint","inquiry","spam","other"]
    sarcasm: bool
    language: Literal["urdu","roman_urdu","english","mixed","emoji_only"]
