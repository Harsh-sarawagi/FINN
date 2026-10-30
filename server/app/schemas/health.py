from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class DatabaseHealthResponse(BaseModel):
    status: str
    database: str


class RootResponse(BaseModel):
    name: str
    status: str
    docs: str
