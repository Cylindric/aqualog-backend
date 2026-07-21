FROM node:20-alpine

WORKDIR /app

# Copy dependency mappings first to utilise Docker build caching
COPY package.json ./
RUN npm install --only=production

# Copy over the proxy application
COPY index.js ./

# Expose the internal SMTP port
EXPOSE 25

# Run the node app directly
CMD ["node", "index.js"]
