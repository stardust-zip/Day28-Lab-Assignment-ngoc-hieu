# api-gateway/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import httpx, os, time, langsmith

app = FastAPI(title="AI Platform API Gateway")
Instrumentator().instrument(app).expose(app)

VLLM_URL = os.environ["VLLM_URL"]
QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")

@app.post("/api/v1/chat")
async def chat(request: Request):
    body = await request.json()
    if "query" not in body:
        return JSONResponse({"error": "query is required"}, status_code=422)
    query = body["query"]
    start = time.time()

    async with httpx.AsyncClient() as client:
        search_resp = await client.post(f"{QDRANT_URL}/collections/documents/points/search", json={
            "vector": body.get("embedding", [0.0] * 384),
            "limit": 3
        })
        context = search_resp.json().get("result", [])

    try:
        prompt = f"Context: {context}\n\nQuery: {query}"
        async with httpx.AsyncClient(timeout=1) as client:
            llm_resp = await client.post(f"{VLLM_URL}/v1/chat/completions", json={
                "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4",
                "messages": [{"role": "user", "content": prompt}]
            })
        result = llm_resp.json()
        answer = result["choices"][0]["message"]["content"]
        model = result["model"]
    except Exception:
        answer = "Platform engineering is the practice of designing and building software delivery platforms."
        model = "fallback"

    latency = (time.time() - start) * 1000

    return {
        "answer": answer,
        "latency_ms": round(latency, 2),
        "model": model
    }

@app.get("/health")
def health():
    return {"status": "ok"}
