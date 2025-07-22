# How to Build from Source

This comprehensive guide provides detailed instructions for building the Smart NVR application container images from source code. Whether you're a developer looking to customize the application or troubleshoot issues, this guide will walk you through the complete build and deployment process.

## Overview

The Smart NVR application consists of multiple components that work together to provide GenAI-powered video analytics:

- **NVR Event Router**: Core backend service that processes events and coordinates between services.
- **UI Component**: Gradio-based web interface for interacting with the system.
- **Frigate VMS**: Video management system for object detection and video processing.
- **MQTT Broker**: Message broker for inter-service communication.
- **Redis**: In-memory data store for caching and managing rules.


## Step 1: Clone the Repository

First, clone the repository and navigate to the Smart NVR directory:

```bash
git clone https://github.com/open-edge-platform/edge-ai-suites.git
cd edge-ai-suites/metro-ai-suite/smart-nvr
```

## Step 2: Build the Docker Images

The application provides a build script to simplify the image building process:

```bash
./build.sh
```

### What the Build Script Does

The `build.sh` script performs the following operations:

1. **Sets Default Values**: Uses `intel/nvr-event-router:latest` as the default image name and tag
2. **Configures Proxy Settings**: Automatically passes through proxy environment variables if set
3. **Builds Docker Image**: Creates the Docker image using the Dockerfile in the `docker/` directory
4. **Validates Build**: Confirms the image was built successfully

### Customizing the Build

You can customize the build process by setting environment variables:

```bash
# Custom image name and tag
export IMAGE_NAME="my-registry/nvr-event-router"
export TAG="v1.0.0"
./build.sh
```
### Building with Copyleft Sources

If you need to include copyleft sources in your build, you can set the following environment variable:

```bash
export ADD_COPYLEFT_SOURCES=true
```

When this environment variable is set to `true`, it allows the Dockerfiles to conditionally include copyleft sources when needed.


## What to Do Next

- **[Get Started](./get-started.md)**: Complete the initial setup and configuration steps
- **[How to Use the Application](./how-to-use-application.md)**: Learn about the application's features and functionality
- **[API Reference](./api-reference.md)**: Explore the available REST API endpoints
- **[Troubleshooting](./support.md#troubleshooting-docker-deployments)**: Find solutions to common deployment issues
- **[System Requirements](./system-requirements.md)**: Review hardware and software requirements

