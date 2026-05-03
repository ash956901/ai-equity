# syntax=docker/dockerfile:1.7
# Build context:        frontend/
# Named build context:  infra -> infrastructure/docker/
#
# Build (local):
#   docker build \
#     -f infrastructure/docker/frontend.Dockerfile \
#     --build-context infra=infrastructure/docker \
#     --build-arg VITE_BACKEND_URL=http://localhost:8001 \
#     -t ai-equity-frontend frontend
#
# The `infra` named context is BuildKit's mechanism for pulling files from
# outside the primary context. CI passes the same flag in deploy.yml.

ARG NODE_VERSION=20

# ---------- build ----------
FROM node:${NODE_VERSION}-alpine AS build

WORKDIR /app

# Vite reads VITE_* env vars at build time and bakes them into the bundle.
# The deploy CI passes VITE_BACKEND_URL via --build-arg so each environment
# (staging, prod) gets its own image tag pointing at the correct API origin.
ARG VITE_BACKEND_URL=http://localhost:8001
ENV VITE_BACKEND_URL=${VITE_BACKEND_URL}

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

RUN npm run build

# ---------- runtime ----------
FROM nginx:alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf
COPY --from=infra nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
