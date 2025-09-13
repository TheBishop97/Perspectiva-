# ---------- Build Stage ----------
FROM node:20 AS builder

WORKDIR /app

# Copy package manifests first (better caching)
COPY package*.json ./

# Install dependencies cleanly
RUN npm ci --legacy-peer-deps

# Copy source code
COPY . .

# Disable Turbopack (use stable SWC compiler)
ENV NEXT_DISABLE_TURBOPACK=1

# Build Next.js app
RUN npm run build

# ---------- Runtime Stage ----------
FROM node:20-alpine AS runner

WORKDIR /app

# Copy only what we need from builder
COPY --from=builder /app/package.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

# Set production environment
ENV NODE_ENV=production

# Expose Next.js port
EXPOSE 3000

# Run Next.js
CMD ["npm", "start"]
