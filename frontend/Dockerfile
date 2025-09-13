# ---------- Builder Stage ----------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install --legacy-peer-deps

COPY . .

# Disable SWC (use Babel instead, portable but slower)
RUN npm run build --no-swc

# ---------- Runtime Stage ----------
FROM node:20-alpine AS runner

WORKDIR /app

COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
