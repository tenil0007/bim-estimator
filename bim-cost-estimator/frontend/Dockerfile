# Frontend Dockerfile
# Multi-stage build: Node for build, Nginx for serving

# Stage 1: Build
FROM node:20-alpine as build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy custom Nginx config
COPY --from=build /app/dist /usr/share/nginx/html

# Nginx config for SPA routing and API proxy
RUN echo 'server { \
    listen 80; \
    server_name localhost; \
    root /usr/share/nginx/html; \
    index index.html; \
    \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    \
    location /api/ { \
        proxy_pass http://backend:8000; \
        proxy_set_header Host $host; \
        proxy_set_header X-Real-IP $remote_addr; \
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; \
        proxy_set_header X-Forwarded-Proto $scheme; \
        proxy_read_timeout 120s; \
        client_max_body_size 500M; \
    } \
    \
    location /docs { \
        proxy_pass http://backend:8000; \
    } \
    \
    location /health { \
        proxy_pass http://backend:8000; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
