from pydantic import BaseModel


class Rule(BaseModel):
    id: str
    label: str
    action: str
    camera: str | None = None
