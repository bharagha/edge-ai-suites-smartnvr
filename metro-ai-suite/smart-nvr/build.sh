#!/bin/bash

export PROJECT_NAME="nvr-event-router"
tag="${PROJECT_NAME}:latest"

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

docker build ${BUILD_ARGS} -t "${tag}" -f docker/Dockerfile .
docker images | grep "$tag" && echo "Image ${tag} built successfully."
