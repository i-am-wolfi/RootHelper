FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY bot.py .
RUN mkdir -p data
CMD ["sh", "-c", "export $(grep -v '^#' bot.env 2>/dev/null | xargs) 2>/dev/null; python bot.py"]
