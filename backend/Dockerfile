# Datails backend container image.
# Runs as a non-root user; no secrets baked in — configuration arrives via
# environment (Key Vault references in Azure).
FROM python:3.12-slim

WORKDIR /srv/datails

RUN adduser --system --group --no-create-home datails

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --chown: the source volume carries restrictive owner-only permissions;
# the runtime user must be able to read the copied tree.
COPY --chown=datails:datails app ./app

USER datails

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
