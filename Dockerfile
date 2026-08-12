FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    POKEDB_DB=/data/pokemon_tcg.sqlite

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY database.xlsx pikaqian_cards.xlsx ./
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh && mkdir -p /data /app/exports

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=180s \
    CMD curl -fsS http://localhost:8000/health || exit 1

ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "pokedb.api:app", "--host", "0.0.0.0", "--port", "8000"]
