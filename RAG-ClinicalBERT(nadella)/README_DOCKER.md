# Running Medical RAG System with Docker

This guide explains how to run the containerized version of the Medical RAG System.

## Prerequisites
- Docker Desktop installed
- `.env` file configured with your API keys

## Quick Start

1. **Build and Start**:
   ```bash
   docker compose up --build
   ```

2. **Access the Application**:
   - Web Interface: http://localhost:5557

3. **Stop the Application**:
   - Press `Ctrl+C` in the terminal
   - Or run: `docker compose down`

## Troubleshooting

- **Database Connection**: The container expects to connect to your Neon database. Ensure your `NEON_CONNECTION_STRING` in `.env` is correct.
- **Data Persistence**: The `data/` directory is mounted as a volume, so any new cases added locally will be visible in the container.
- **Logs**: Check logs with `docker compose logs -f`.
