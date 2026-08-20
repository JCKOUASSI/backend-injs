# Build Vite → nginx (spa)
#
# Contexte de build : la racine du dépôt (le SPA importe les sources de
# eptinjs/frontend via l'alias @eptinjs). Construire avec :
#   docker build -f ings-fe/Dockerfile .
FROM node:22-alpine AS build

WORKDIR /app/ings-fe

COPY ings-fe/package.json ings-fe/package-lock.json ./
RUN npm ci

COPY ings-fe/ ./

# L'alias @eptinjs de vite.config.js pointe vers ../eptinjs/frontend : la
# disposition du dépôt doit être conservée dans l'image.
COPY eptinjs/frontend /app/eptinjs/frontend

ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/ings-fe/dist /usr/share/nginx/html
COPY ings-fe/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
