# Resonance web app + API in one container. Runs and accounts live in /data (mount a volume).
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY resonance ./resonance
RUN pip install --no-cache-dir .
WORKDIR /data
ENV RESONANCE_DAILY_ANALYSES=5 \
    RESONANCE_DAILY_DIAGNOSES=3 \
    RESONANCE_DAILY_BUDGET_USD=10
EXPOSE 8000
VOLUME /data
CMD ["resonance", "serve", "--host", "0.0.0.0", "--port", "8000"]
