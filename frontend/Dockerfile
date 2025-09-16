# ---------- Runtime Stage ----------
FROM node:20-alpine AS runner
WORKDIR /app

# Copy standalone build from Codespaces build
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public

# Expose Next.js default port
EXPOSE 3000

# Run production server
CMD ["node", "server.js"]
