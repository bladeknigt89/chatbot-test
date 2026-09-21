FROM node:20-alpine AS build
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json* /web/
RUN npm install
COPY frontend /web
RUN npm run build
