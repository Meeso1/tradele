from pydantic import BaseModel


class MetadataResponse(BaseModel):
    day_number: int
    seconds_until_day_end: int
    has_completed_tutorial: bool
