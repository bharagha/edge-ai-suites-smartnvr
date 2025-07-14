# Release Notes


## Current Release
**Version**: RC1 
**Release Date**: 14 July 2025  

**Features**:
• Smart NVR backend and frontend based on the single docker image
• Gradio based UI for selecting the use case
• Docker compose based deployment for the E2E application
• Auto Routing of the NVR events
• Routing of the events based on the timestamp
• Showcasing Using NVR's Event routing capabilities to OEP VLM microservice

**Core Application Features**:
• **Video Summarization & Search**
  - Timestamp-based video selection from Frigate NVR recordings
  - Flexible duration control for custom video clip lengths
  - AI-powered search integration with VSS (Video Search Service)
  - Intelligent summarization with AI-driven content analysis
  - Pipeline status monitoring for real-time processing tracking
  - Seamless Frigate integration for automatic video clip retrieval

• **AI-Powered Event Viewer**
  - Vision Language Model (VLM) integration for natural language event descriptions
  - Multi-camera support with intuitive interface
  - Real-time event processing and analysis
  - Detailed event descriptions with contextual understanding
  - Interactive event timeline for historical event browsing
  - Enhanced scene understanding beyond basic object detection

• **Automated Event Routing**
  - Rule-based event processing with custom triggers
  - MQTT broker integration for real-time NVR communication
  - VSS search integration for automatic event clip indexing
  - VSS summary integration for automated event summarization
  - Flexible rule configuration supporting complex criteria
  - Multi-camera rule support across entire camera networks


**HW used for validation**:
- Intel® Xeon® 5 + Intel® Arc&trade; B580 GPU

**Known Issues/Limitations**:
- EMF and EMT are not supported yet.
- Users are required to build the images and use the sample application. Docker images are not available yet on public registries (pending approvals).

## Previous releases

**Version**:  \
**Release Date**:  

- <Previous release notes>
