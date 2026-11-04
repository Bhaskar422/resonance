# Resonance web app + API in one container. Runs and accounts live in /data (mount a volume).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY resonance ./resonance
# exact versions from uv.lock (with hashes), so a rebuild never pulls a newer release
RUN uv export --frozen --no-dev --no-emit-project -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir --no-deps . \
    && rm /tmp/requirements.txt
WORKDIR /data
ENV RESONANCE_DAILY_ANALYSES=5 \
    RESONANCE_DAILY_DIAGNOSES=3 \
    RESONANCE_DAILY_BUDGET_USD=10
EXPOSE 8000
VOLUME /data
CMD ["resonance", "serve", "--host", "0.0.0.0", "--port", "8000"]
