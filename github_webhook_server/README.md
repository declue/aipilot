# GitHub Webhook Server

A robust server for receiving, storing, and relaying GitHub webhook events.

## Features

- **Webhook Reception**: Securely receive and validate GitHub webhook events
- **Event Storage**: Store webhook events in JSON files for persistence
- **Client Management**: Register clients with specific interests (organizations, repositories)
- **Event Polling**: Clients can poll for new events that match their interests
- **API Documentation**: Interactive API documentation with Swagger UI
- **Security**: Webhook signature verification, CORS support, rate limiting
- **Monitoring**: Health checks, server information, and file listing endpoints
- **Logging**: Comprehensive logging with rotation and retention policies

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd github_webhook_server
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables (optional):
   ```bash
   # Create a .env file
   touch .env
   
   # Add configuration variables
   echo "GITHUB_WEBHOOK_SECRET=your_webhook_secret" >> .env
   echo "WEBHOOK_HOST=0.0.0.0" >> .env
   echo "WEBHOOK_PORT=8000" >> .env
   echo "LOG_LEVEL=info" >> .env
   echo "ENABLE_CORS=false" >> .env
   echo "RATE_LIMIT_ENABLED=true" >> .env
   echo "RATE_LIMIT=100" >> .env
   ```

## Usage

### Starting the Server

```bash
python main.py
```

The server will start on http://localhost:8000 by default.

### API Documentation

Once the server is running, you can access the API documentation at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

### Configuring GitHub Webhooks

1. Go to your GitHub repository or organization settings
2. Navigate to "Webhooks" and click "Add webhook"
3. Set the Payload URL to your server's webhook endpoint (e.g., `http://your-server:8000/api/v1/webhook`)
4. Set Content type to `application/json`
5. (Optional) Set a secret for secure verification
6. Choose which events to send
7. Click "Add webhook"

### Registering a Client

```bash
curl -X POST "http://localhost:8000/api/v1/clients" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-client",
    "description": "My webhook client",
    "interested_orgs": ["microsoft", "google"],
    "interested_repos": ["microsoft/vscode", "google/gson"]
  }'
```

### Polling for Events

```bash
curl -X GET "http://localhost:8000/api/v1/clients/poll/1"
```

## API Endpoints

### Webhook Endpoints

- `POST /api/v1/webhook` - Receive GitHub webhook events

### Client Endpoints

- `POST /api/v1/clients` - Register a new client
- `GET /api/v1/clients` - List all clients
- `GET /api/v1/clients/{client_id}` - Get a specific client
- `GET /api/v1/clients/poll/{client_id}` - Poll for new messages

### System Endpoints

- `GET /api/v1/` - Get server information
- `GET /api/v1/health` - Check server health
- `GET /api/v1/files` - List saved webhook files

## Testing

### Using the Simulator

The project includes a simulator for testing webhook events:

```bash
python simulator.py
```

This will open a GUI application that allows you to:
- Configure the webhook URL
- Set repository and organization details
- Select event types and actions
- Send simulated webhook events to the server

## Configuration

The server can be configured using environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_WEBHOOK_SECRET` | Secret for webhook signature verification | "" |
| `WEBHOOK_HOST` | Host to bind the server to | "0.0.0.0" |
| `WEBHOOK_PORT` | Port to bind the server to | 8000 |
| `LOG_LEVEL` | Logging level | "info" |
| `ENABLE_CORS` | Enable CORS support | false |
| `CORS_ORIGINS` | Allowed origins for CORS | "*" |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | false |
| `RATE_LIMIT` | Rate limit (requests per minute) | 100 |

## Project Structure

```
github_webhook_server/
├── data/                  # Webhook data storage
├── logs/                  # Log files
├── webhook/               # Core package
│   ├── __init__.py        # Package initialization
│   ├── api.py             # API endpoints
│   ├── config.py          # Configuration settings
│   ├── models.py          # Database models
│   ├── schemas.py         # Pydantic schemas
│   └── utils.py           # Utility functions
├── main.py                # Main application entry point
├── requirements.txt       # Dependencies
├── simulator.py           # Webhook simulator
└── README.md              # This file
```

## License

[MIT License](LICENSE)