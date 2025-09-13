# ---------- Builder Stage ----------
FROM node:20-bullseye AS builder

# Set working directory
WORKDIR /app

# Copy package.json and lock file
COPY package*.json ./

# Install dependencies (clean install)
RUN npm ci --legacy-peer-deps

# Copy rest of the source code
COPY . .

# Build Next.js app
RUN npm run build

# ---------- Runtime Stage ----------
FROM node:20-alpine AS runner

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000

CMD ["npm", "start"]
