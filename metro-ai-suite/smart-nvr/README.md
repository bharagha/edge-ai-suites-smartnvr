# NVR Event Router

A microservice that interfaces with Frigate VMS (Video Management System) to route events to summarization or search pipelines. The service includes a FastAPI backend and a Gradio-based user interface.

## Components

### 1. API Service

A FastAPI-based service that provides endpoints for:
- Fetching camera and event information from Frigate
- Getting video clips for specific time ranges
- Retrieving event information
- Sending videos for summarization or search.

### 2. Gradio UI

A user-friendly interface that allows users to:
- Monitor real-time events from Frigate VMS
- Select time ranges for video processing and videos for summarization or search indexing

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌────────────────────┐
│             │    │              │    │                    │
│  Frigate    │◄───┤ NVR Event    │◄───┤  Gradio UI        │
│  VMS        │    │ Router API   │    │                    │
│             │    │              │    │                    │
└─────────────┘    └──────┬───────┘    └────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │              │
                   │ Summary      │
                   │ Service      │
                   │              │
                   └──────────────┘
```

## Requirements

- Docker and Docker Compose
- Python 3.8+
- FastAPI
- Gradio 4.0+
- Requests

## Environment Variables

### API Service

You need to provide the following variables:

- `FRIGATE_IP`: IP address of the Frigate VMS (required)
- `FRIGATE_PORT`: Port of the Frigate VMS (required, typically 5000)
- `VSS_SUMMARY_IP`: IP address of the Video Summarization Service (required)
- `VSS_SUMMARY_PORT`: Port of the Video Summarization Service (required, typically 12345)
- `VSS_SEARCH_IP`: IP address of the Video Summarization Service (required)
- `VSS_SEARCH_PORT`: Port of the Video Summarization Service (required, typically 12345)
- `VLM_MODEL_IP`: IP address of the VLM Model Endpoint (required)
- `VLM_MODEL_PORT`: Port of the VLM Model Endpoint (required, typically 9766)
- `MQTT_USER`: Username for the MQTT broker (required)
- `MQTT_PASSWORD`: Password for the MQTT broker (required)

These will be used to construct:
- `FRIGATE_BASE_URL`: http://${FRIGATE_IP}:${FRIGATE_PORT}
- `VSS_SEARCH_URL`: http://${VSS_SEARCH_IP}:${VSS_SEARCH_PORT}
- `VSS_SUMMARY_URL`: http://${VSS_SUMMARY_IP}:${VSS_SUMMARY_PORT}
- `VLM_MODEL_ENDPOINT`: http://${VLM_MODEL_IP}:${VLM_MODEL_PORT}/v1

### UI Service

- `API_BASE_URL`: URL of the NVR Event Router API
- `EVENT_POLL_INTERVAL`: How often to poll for new events (in seconds)

> **Important**: You must provide the IP and port information for both services when running the application. The run.sh script will check for these required variables and exit with an error if they're not provided.

## Running the Service

### 1. Build the Docker Image

```bash
# Set required environment variables (FRIGATE_IP, FRIGATE_PORT, etc.)
export FRIGATE_IP="192.168.1.2"     # Replace with your Frigate VMS IP
export FRIGATE_PORT="5000"            # Replace with your Frigate VMS port
export VSS_IP="192.168.1.2"         # Replace with your VSS IP
export VSS_PORT="12345"               # Replace with your VSS port
export VLM_MODEL_IP="192.168.1.2"   # Replace with your VLM Model Endpoint IP
export VLM_MODEL_PORT="9766"          # Replace with your VLM Model Endpoint port
export MQTT_USER=""            # Replace with your MQTT username
export MQTT_PASSWORD=""           # Replace with your MQTT password

# Build the Docker image
./build.sh
```

### 2. Start the Services

```bash
# Then start all services
source setup.sh
```

If you're running services on the same machine, you can set all IPs to your machine's IP address:

### Accessing the Services

- API: http://localhost:8000
- UI: http://localhost:7860
- Frigate VMS: http://localhost:5000 (if using the default configuration)

## API Documentation

API documentation is automatically generated and available at:
- http://localhost:8000/docs (Swagger UI)
