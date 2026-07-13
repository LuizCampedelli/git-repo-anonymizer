FROM python:3.11-slim

WORKDIR /app

# Ensure output streams handle Docker logs natively
ENV PYTHONUNBUFFERED=1

COPY anonymizer.py .

# Define mount targets for runtime execution
VOLUME [ "/app/src", "/app/sanitized" ]

CMD ["python", "anonymizer.py"]
