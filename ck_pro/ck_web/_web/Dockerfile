# ============================================================================
# CognitiveKernel-Pro Web Server Dockerfile
# ============================================================================
# Based on Playwright official image with automatic browser version matching
# ============================================================================

# Use specific Playwright image version (includes browsers)
FROM mcr.microsoft.com/playwright:v1.46.1-focal

# Set environment variables
ENV NODE_ENV=production \
    LISTEN_PORT=9000 \
    MAX_BROWSERS=16 \
    USER_UID=1001 \
    USER_GID=1001 \
    APP_USER=ckweb \
    DOCKER_CONTAINER=true

# Create non-privileged user
RUN groupadd -g ${USER_GID} ${APP_USER} && \
    useradd -u ${USER_UID} -g ${USER_GID} -m -s /bin/bash ${APP_USER}

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json ./
RUN npm install --only=production && npm cache clean --force

# Copy application code
COPY --chown=${APP_USER}:${APP_USER} . .

# Create necessary directories
RUN mkdir -p ./DownloadedFiles ./screenshots && \
    chown -R ${APP_USER}:${APP_USER} ./DownloadedFiles ./screenshots

# Copy entrypoint script
COPY --chown=${APP_USER}:${APP_USER} entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-privileged user
USER ${APP_USER}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${LISTEN_PORT}/health || exit 1

# Expose port
EXPOSE ${LISTEN_PORT}

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["npm", "start"]
