FROM python:3.10-slim

WORKDIR /app

# Copy the uv binary from the official uv image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Use uv pip install for incredibly fast system-wide installation
RUN uv pip install --system fastapi uvicorn httpx prometheus-fastapi-instrumentator langsmith

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
