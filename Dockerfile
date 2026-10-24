FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .
RUN pip install -e . --no-cache-dir

COPY .env.example .env.example

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "readme_gen"]
CMD ["generate", "/workspace"]