from pydantic import BaseModel

class Sampling(BaseModel):
    chunkDuration: int
    samplingFrame: int

class Evam(BaseModel):
    evamPipeline: str

class SummaryPayload(BaseModel):
    videoId: str
    title: str
    sampling: Sampling
    evam: Evam