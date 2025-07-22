#!/bin/bash

# Set default values for IMAGE_NAME and TAG if not provided via environment variables
IMAGE_NAME="${IMAGE_NAME:-intel/nvr-event-router}"
TAG="${TAG:-latest}"
tag="${IMAGE_NAME}:${TAG}"

echo "Building $tag image..."

BUILD_ARGS=""
if [ -n "${http_proxy}" ]; then
    BUILD_ARGS="${BUILD_ARGS} --build-arg http_proxy=${http_proxy}"
fi
if [ -n "${https_proxy}" ]; then
    BUILD_ARGS="${BUILD_ARGS} --build-arg https_proxy=${https_proxy}"
fi
if [ -n "${no_proxy}" ]; then
    BUILD_ARGS="${BUILD_ARGS} --build-arg no_proxy=${no_proxy}"
fi

# Add copyleft sources build arg if environment variable is set
if [ "$ADD_COPYLEFT_SOURCES" = "true" ]; then
BUILD_ARGS="$BUILD_ARGS --build-arg COPYLEFT_SOURCES=true"
fi

docker build ${BUILD_ARGS} -t "${tag}" -f docker/Dockerfile .
docker images | grep "$tag" && echo "Image ${tag} built successfully."
