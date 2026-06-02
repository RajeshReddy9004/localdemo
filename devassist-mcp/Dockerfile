FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate --noinput

EXPOSE 8000

# Default: run the Django backend (admin + REST API).
# To run the MCP server instead:  docker run ... python mcp_server/server.py
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
