FROM node:current-alpine

# Defaults to production, docker-compose overrides this to development on build and run.
ARG NODE_ENV=production
ENV NODE_ENV=$NODE_ENV

# Update system packages
RUN apk update \
 && apk add --no-cache curl \
 && apk upgrade \
 && rm -rf /var/cache/apk/* \
 && apk cache clean

# Update system packages identified by Trivy to fix vulnerabilities
RUN npm update --no-fund -g npm \
 && npm update --no-fund -g tar \
 && npm cache clean --force

# Setup the working directory
WORKDIR /app
RUN chown node:node /app
USER node

# Copy dependency mappings first to utilise Docker build caching
COPY package.json package-lock.json ./
RUN npm ci \
 && npm cache clean --force

# Copy over the proxy application
COPY index.js ./

# Expose the internal SMTP port
EXPOSE 25

# Run the node app directly
CMD ["node", "index.js"]
