#!/bin/bash

export PROJECT_NAME="nvr-event-router"

# Optional: set a registry, e.g., "myregistry.io/" or leave it blank
export REGISTRY="${REGISTRY:-}"

# Construct the image tag
tag="${PROJECT_NAME}:latest"


# Get the host IP address
get_host_ip() {
    # Try different methods to get the host IP
    if command -v ip &> /dev/null; then
        # Use ip command if available (Linux)
        HOST_IP=$(ip route get 1 | sed -n 's/^.*src \([0-9.]*\) .*$/\1/p')
    elif command -v ifconfig &> /dev/null; then
        # Use ifconfig if available (Linux/Mac)
        HOST_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -n 1)
    else
        # Fallback to hostname command
        HOST_IP=$(hostname -I | awk '{print $1}')
    fi
    
    # Fallback to localhost if we couldn't determine the IP
    if [ -z "$HOST_IP" ]; then
        HOST_IP="localhost"
        echo "Warning: Could not determine host IP, using localhost instead."
    fi
    
    echo "$HOST_IP"
}

# Function to validate required environment variables
validate_environment() {
    # Check for Frigate VMS IP and port
    if [ -z "${FRIGATE_IP}" ]; then
        echo "Error: FRIGATE_IP environment variable is required"
        echo "Please set it to the IP address of your Frigate VMS"
        return 1
    fi
    
    if [ -z "${FRIGATE_PORT}" ]; then
        echo "Error: FRIGATE_PORT environment variable is required"
        echo "Please set it to the port of your Frigate VMS (typically 5000)"
        return 1
    fi
    
    # Check for VSS IP and port
    if [ -z "${VSS_SUMMARY_IP}" ]; then
        echo "Error: VSS_SUMMARY_IP environment variable is required"
        echo "Please set it to the IP address of your Video Summarization Service"
        return 1
    fi
    
    if [ -z "${VSS_SUMMARY_PORT}" ]; then
        echo "Error: VSS_SUMMARY_PORT environment variable is required"
        echo "Please set it to the port of your Video Summarization Service (typically 12345)"
        return 1
    fi
    # Check for VSS IP and port
    if [ -z "${VSS_SEARCH_IP}" ]; then
        echo "Error: VSS_SEARCH_IP environment variable is required"
        echo "Please set it to the IP address of your Video Summarization Service"
        return 1
    fi
    
    if [ -z "${VSS_SEARCH_PORT}" ]; then
        echo "Error: VSS_SEARCH_PORT environment variable is required"
        echo "Please set it to the port of your Video Summarization Service (typically 12345)"
        return 1
    fi
    
    # Check for VLM Model Endpoint IP and port
    if [ -z "${VLM_MODEL_IP}" ]; then
        echo "Error: VLM_MODEL_IP environment variable is required"
        echo "Please set it to the IP address of your VLM Model Endpoint"
        return 1
    fi
    
    if [ -z "${VLM_MODEL_PORT}" ]; then
        echo "Error: VLM_MODEL_PORT environment variable is required"
        echo "Please set it to the port of your VLM Model Endpoint (typically 9766)"
        return 1
    fi
    
    # Check for MQTT user and password
    if [ -z "${MQTT_USER}" ]; then
        echo "Error: MQTT_USER environment variable is required"
        return 1
    fi
    
    if [ -z "${MQTT_PASSWORD}" ]; then
        echo "Error: MQTT_PASSWORD environment variable is required"
        return 1
    fi
}

# Function to start the services
start_services() {
    HOST_IP=$(get_host_ip)
    
    # Validate environment variables and exit if validation fails
    if ! validate_environment; then
        echo "Error: Environment validation failed. Please set the required variables."
        return 1
    fi
    
    # Run the Docker Compose stack with all services
    docker compose -f docker/compose.yaml up -d 

    echo "Services are starting up..."
    echo "- API will be available at: http://${HOST_IP}:8000"
    echo "- UI will be available at: http://${HOST_IP}:7860"
}

# Function to stop the services
stop_services() {
    echo "Stopping NVR Event Router services..."
    export HOST_IP=$(get_host_ip)
    docker compose -f docker/compose.yaml down
    echo "All services stopped."
}

# Function to display help
show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start all services (default if no command provided)"
    echo "  stop     - Stop all services"
    echo "  restart  - Restart all services"
    echo "  help     - Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start     # Start the services"
    echo "  $0 stop      # Stop the services"
    echo "  $0           # Same as 'start' (for backward compatibility)"
    echo ""
}

# Main script logic
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        # Default behavior (backwards compatibility)
        start_services
        ;;
esac