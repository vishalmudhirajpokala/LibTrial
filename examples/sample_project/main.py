"""FastAPI analytics sample service."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="FastAnalytics")


class QueryRequest(BaseModel):
    query: str
    limit: int = 100


@app.get("/")
def root():
    return {"status": "healthy", "service": "fast-analytics"}


@app.post("/query")
def process_query(req: QueryRequest):
    return {"query": req.query, "matched_records": req.limit}
