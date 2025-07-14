# Get Help

This page provides comprehensive support and troubleshooting information for the Smart NVR Sample Application. It is divided into the following sections:

  - **Common Issues**: General troubleshooting steps for resolving issues like container failures, port conflicts, and missing dependencies.
  - **Troubleshooting Docker Deployments**: Steps to address problems specific to Docker deployments.

## Troubleshooting Common Issues

### 1. Containers Not Starting
- **Issue**: The application containers fail to start.
- **Solution**:

  ```bash
  docker ps
  docker logs <container-id>
  ```
  Check the logs for errors.

### 2. Port Conflicts
- **Issue**: Port conflicts with other running applications.
- **Solution**: Update the ports section in the Docker Compose file.
  
### 3. Description not coming in UI
- Check logs for frigate container
- Check if VLM microservice is running and reachable.

### 4. Object not getting detected 
- Check the label in frigate config.yaml for the specific camera
- Check the top_score parameter 

## Troubleshooting Docker Containers

### 1. Containers Failing:
   - Check the Docker logs for errors:
     ```bash
     docker ps
     docker logs <container-id>
     ```
### 2. Port Conflicts:
   - Update the `ports` section in the Compose file to resolve conflicts.
### 3. Reset Application:
   - Follow these steps to reset the application to the initial state
     ```bash
     ./setup.sh stop
     docker volume ls | grep nvr-event-router | awk '{ print $2 }' | xargs docker volume rm
     ```
<!--
## Support
- **Developer Forum**: Join the community forum
- **Contact Support**: [Support Page](#)
-->
