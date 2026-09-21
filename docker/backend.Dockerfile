FROM node:20-alpine AS frontend
WORKDIR /web
COPY frontend/package.json /web/package.json
RUN npm install
COPY frontend /web
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY chat-widget /app/chat-widget
COPY --from=frontend /web/dist /app/frontend/dist
COPY .env.example /app/.env.example
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
