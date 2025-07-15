# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
#!/usr/bin/env python3
"""
NVR Event Router UI - Gradio Interface

This application provides a user interface for interacting with the NVR Event Router API,
which interfaces with Frigate VMS to route events to summarization or search pipelines.
"""

import os
import json
import time
import logging
import threading
import requests
import tempfile
import pytz
from typing import Dict, List, Optional, Tuple, Any, Union
from inspect import currentframe
from dotenv import load_dotenv
from datetime import datetime, timezone
import gradio as gr

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("vms_event_router_ui.log")],
)
logger = logging.getLogger(__name__)

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL")
EVENT_POLL_INTERVAL = int(os.getenv("EVENT_POLL_INTERVAL", "10"))  # seconds
IST = pytz.timezone("Asia/Kolkata")
# Global variables
camera_list = []
recent_events = []
event_update_thread = None
stop_event_thread = threading.Event()


def format_timestamp(timestamp: Optional[float]) -> str:
    """Convert a Unix timestamp to a human-readable datetime string."""
    logger.debug(f"Formatting timestamp: {timestamp}")
    if timestamp is None:
        logger.warning("Received None timestamp")
        return "N/A"
    try:
        formatted = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        logger.debug(f"Formatted timestamp: {timestamp} -> {formatted}")
        return formatted
    except Exception as e:
        logger.error(f"Error formatting timestamp {timestamp}: {e}")
        return "Invalid Timestamp"


def parse_datetime(datetime_str: str) -> float:
    """Convert a datetime string to a Unix timestamp."""
    logger.info(f"Parsing datetime string: {datetime_str}")
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        timestamp = dt.timestamp()
        logger.debug(f"Parsed datetime: {datetime_str} -> {timestamp}")
        return timestamp
    except ValueError as e:
        logger.error(f"Error parsing datetime '{datetime_str}': {e}")
        return 0  # Return 0 instead of None to avoid type errors


def fetch_cameras() -> List[str]:
    """Fetch the list of available cameras from the API."""
    logger.info(f"Fetching camera list from API: {API_BASE_URL}/cameras")

    try:
        start_time = time.time()
        response = requests.get(f"{API_BASE_URL}/cameras", timeout=10)
        response_time = time.time() - start_time
        logger.info(f"Camera list API response time: {response_time:.2f}s")

        response.raise_for_status()
        cameras = response.json().get("cameras", [])
        logger.info(f"Successfully fetched {len(cameras)} cameras: {cameras}")
        return cameras
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching cameras: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in fetch_cameras: {e}")
        return []


def fetch_events(camera_name: str) -> List[Dict]:
    """Fetch events for a specific camera."""
    logger.info(f"Fetching events for camera: {camera_name}")

    try:
        start_time = time.time()
        response = requests.get(
            f"{API_BASE_URL}/events", params={"camera": camera_name}, timeout=15
        )
        response_time = time.time() - start_time
        logger.info(f"Events API response time: {response_time:.2f}s")

        response.raise_for_status()
        events = response.json()
        logger.info(f"Fetched {len(events)} events for camera {camera_name}")

        # Sort events by start time (most recent first)
        events.sort(key=lambda x: x.get("start_time", 0), reverse=True)
        logger.debug(f"First event: {events[0] if events else 'No events'}")
        return events
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching events for camera {camera_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in fetch_events: {e}")
        return []


def process_video(
    camera_name: str,
    start_time_input: Union[str, float, datetime, None],
    end_time_input: Union[str, float, datetime, None],
    action: str,
    label: str = None,
) -> Dict:
    """Process a video clip for summarization or search."""
    logger.info(f"Processing video request - Camera: {camera_name}, Action: {action}")
    logger.debug(f"Raw inputs - start: {start_time_input}, end: {end_time_input}")

    def parse_input_to_timestamp(
        input_val, label: str
    ) -> Tuple[Optional[float], Optional[str]]:
        """
        Convert inputs to IST timestamp and formatted string.
        Returns: (timestamp, formatted_string) or (None, None) on error

        Handles all inputs as IST timezone:
        - Timezone-aware datetime objects are converted to IST
        - Timezone-naive objects are assumed to be IST
        - ISO strings without timezone are treated as IST
        - Unix timestamps are interpreted as UTC and converted to IST
        """
        try:
            dt = None

            # Handle datetime objects
            if isinstance(input_val, datetime):
                if input_val.tzinfo is None:
                    logger.debug(f"Naive datetime received for {label}, assuming IST")
                    dt = IST.localize(input_val)  # Convert naive to IST
                else:
                    dt = input_val.astimezone(IST)  # Convert to IST

            # Handle ISO format strings
            elif isinstance(input_val, str):
                dt = datetime.fromisoformat(input_val)
                if dt.tzinfo is None:
                    logger.debug(
                        f"Naive datetime from ISO string for {label}, assuming IST"
                    )
                    dt = IST.localize(dt)
                else:
                    dt = dt.astimezone(IST)

            # Handle Unix timestamps (always UTC)
            elif isinstance(input_val, (float, int)):
                logger.debug(f"Timestamp input for {label}, converting UTC to IST")
                dt = datetime.fromtimestamp(input_val, tz=pytz.utc).astimezone(IST)

            elif input_val is None:
                logger.warning(f"{label} is None")
                return None, None

            else:
                logger.error(f"Invalid {label} type: {type(input_val)}")
                return None, None

            # Return IST timestamp and formatted string
            timestamp = dt.timestamp()  # Note: This returns POSIX timestamp (UTC-based)
            readable = dt.strftime("%Y-%m-%d %H:%M:%S %Z")  # Shows IST timezone
            logger.debug(
                f"Converted {label} to IST: {readable} (timestamp: {timestamp})"
            )

            return timestamp, readable

        except Exception as e:
            logger.error(f"Failed to parse {label}: {e}", exc_info=True)
            return None, None

    # Convert both start and end
    start_time, start_time_str = parse_input_to_timestamp(
        start_time_input, "start_time"
    )
    end_time, end_time_str = parse_input_to_timestamp(end_time_input, "end_time")

    logger.info(f"Processed start_time: {start_time} ({start_time_str})")
    logger.info(f"Processed end_time: {end_time} ({end_time_str})")

    # Validation
    if start_time is None or end_time is None:
        return {"status": "error", "message": "Please select valid start and end times"}
    if start_time >= end_time:
        return {
            "status": "error",
            "message": "Start time must be earlier than end time",
        }

    try:
        if action == "Summarize":
            logger.info(
                f"Initiating summarization for {camera_name} from {start_time_str} to {end_time_str}"
            )
            start_api_time = time.time()

            response = requests.get(
                f"{API_BASE_URL}/summary/{camera_name}",
                params={"start_time": start_time, "end_time": end_time},
                timeout=30,
            )

            api_time = time.time() - start_api_time
            logger.info(f"Summarization API call took {api_time:.2f} seconds")

            response.raise_for_status()
            result = response.json()
            summary_id = result.get("summary_id", "N/A")

            return {
                "status": "success",
                "message": f"Video sent for summarization. Summary ID: {summary_id}",
                "summary_id": summary_id,
                "processing_time": api_time,
            }

        elif action == "Add to Search":
            logger.warning("Search functionality requested but not yet implemented")
            return {
                "status": "info",
                "message": "Search functionality not yet implemented",
                "camera": camera_name,
                "time_range": f"{start_time_str} to {end_time_str}",
            }

        else:
            logger.error(f"Unknown action requested: {action}")
            return {"status": "error", "message": f"Unknown action: {action}"}

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return {
            "status": "error",
            "message": f"API Error: {str(e)}",
            "error_type": type(e).__name__,
        }

    except Exception as e:
        logger.error(f"Unexpected error in process_video: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}",
            "error_type": type(e).__name__,
        }


def display_events() -> List[List]:
    """Format events for display in a table."""
    logger.info(f"Displaying {len(recent_events)} events in table")

    formatted_events = []
    for event in recent_events:
        try:
            top_score = "NA"
            description = "N/A"
            if event.get("data") and "description" in event.get("data", {}):
                top_score = event.get("data", {}).get("top_score", "N/A")
                description = event.get("data", {}).get("description", "N/A")

            # Handle thumbnail data
            thumbnail = event.get("thumbnail", "")
            if thumbnail:
                # Create HTML img tag for base64 thumbnail
                thumbnail_html = f'<img src="data:image/jpeg;base64,{thumbnail}" style="width:80px;height:60px;object-fit:cover;" alt="Event Thumbnail">'
            else:
                thumbnail_html = "No Image"

            formatted_row = [
                str(event.get("label", "N/A")),
                str(format_timestamp(event.get("start_time"))),
                str(format_timestamp(event.get("end_time"))),
                str(top_score),
                str(description),
                thumbnail_html,
            ]

            # Enforce row is a list, not a tuple
            formatted_events.append(list(formatted_row))
        except Exception as e:
            logger.error(f"Error formatting event {event}: {e}")
            continue

    # Defensive fix: convert all rows to lists
    formatted_events = [list(row) for row in formatted_events]

    return formatted_events if formatted_events else []


def stop_event_updates():
    """Stop the event update thread."""
    global stop_event_thread, event_update_thread
    logger.info("Attempting to stop event update thread")

    if event_update_thread and event_update_thread.is_alive():
        logger.info("Thread is active - sending stop signal")
        stop_event_thread.set()
        event_update_thread.join(timeout=2.0)

        if event_update_thread.is_alive():
            logger.warning("Thread did not stop gracefully")
        else:
            logger.info("Thread stopped successfully")
    else:
        logger.info("No active thread to stop")


def initialize_app():
    """Initialize the application and fetch required data."""
    global camera_list
    logger.info("Initializing application")

    try:
        start_time = time.time()
        camera_list = fetch_cameras()
        init_time = time.time() - start_time

        logger.info(f"Initialized with {len(camera_list)} cameras in {init_time:.2f}s")
        return camera_list
    except Exception as e:
        logger.error(f"Initialization failed: {e}", exc_info=True)
        return []


def create_ui():
    """Create the Gradio interface."""
    logger.info("Starting UI creation")

    theme = gr.themes.Base(
        primary_hue="blue",
        secondary_hue="indigo",
    )

    with gr.Blocks(title="NVR Event Router", theme=theme) as interface:
        logger.info("Setting up main interface blocks")
        gr.Markdown(
            "Monitor and process events from Frigate VMS using OEP Video Search and Summarization Application."
        )

        def refresh_camera_lists():
            logger.info("Refreshing camera lists")
            cameras = initialize_app()
            logger.info(f"Refreshed camera list with {len(cameras)} cameras")
            return cameras, cameras, cameras

        with gr.Tabs():
            # Camera Events Tab
            with gr.TabItem("AI-Powered Event Viewer"):
                logger.info("Creating Event Viewer tab")

                with gr.Row():
                    with gr.Column(scale=1):
                        camera_events_dropdown = gr.Dropdown(
                            choices=camera_list,
                            label="Select Camera",
                            interactive=True,
                            container=True,
                        )
                    with gr.Column(scale=2):
                        gr.HTML("")

                events_table = gr.Dataframe(
                    headers=[
                        "Label",
                        "Start Time",
                        "End Time",
                        "Top Score",
                        "Description",
                        "Thumbnail",
                    ],
                    datatype=["str", "str", "str", "str", "str", "html"],
                    label="Events",
                    interactive=False,
                    elem_id="events-table",
                    elem_classes="events-table",
                )
                gr.HTML(
                    """
                <style>
                .events-table table td:nth-child(5) {
                    white-space: normal !important;
                    word-wrap: break-word !important;
                    max-width: 300px;
                }
                .events-table table td:nth-child(6) {
                    text-align: center;
                    vertical-align: middle;
                }
                .events-table table td:nth-child(6) img {
                    border-radius: 4px;
                    border: 1px solid #ddd;
                }
                </style>
                """
                )

                def fetch_and_display_events(camera_name):
                    global recent_events
                    logger.info(f"Fetching events for camera: {camera_name}")

                    if camera_name:
                        start_time = time.time()
                        recent_events = fetch_events(camera_name)
                        fetch_time = time.time() - start_time

                        logger.info(
                            f"Fetched events in {fetch_time:.2f}s, displaying {len(recent_events)} events"
                        )
                        formatted_events = display_events()

                        # Ensure we're returning a list of lists
                        if not isinstance(formatted_events, list):
                            logger.error(
                                f"Unexpected return type from display_events: {type(formatted_events)}"
                            )
                            return []
                        if formatted_events and not isinstance(
                            formatted_events[0], list
                        ):
                            logger.error(
                                f"Unexpected inner type from display_events: {type(formatted_events[0])}"
                            )
                            return []

                        return formatted_events
                    else:
                        logger.warning("No camera selected")
                        return []

                camera_events_dropdown.change(
                    fn=lambda camera: (
                        logger.info(f"Camera changed to: {camera}"),
                        fetch_and_display_events(camera),
                    )[1],
                    inputs=[camera_events_dropdown],
                    outputs=[events_table],
                )

            # Process Video Tab
            with gr.TabItem("Summarize/Search Clips"):
                logger.info("Creating Process Video tab")

                with gr.Row():
                    with gr.Column(scale=2):
                        camera_dropdown = gr.Dropdown(
                            choices=camera_list,
                            label="Select Camera",
                            interactive=True,
                            container=True,
                        )

                    with gr.Column(scale=4):
                        with gr.Row():
                            with gr.Column(scale=1):
                                start_time_input = gr.DateTime(
                                    label="Start Time",
                                    interactive=True,
                                )
                            with gr.Column(scale=1):
                                end_time_input = gr.DateTime(
                                    label="End Time",
                                    interactive=True,
                                )

                    with gr.Column(scale=2):
                        action_dropdown = gr.Dropdown(
                            choices=["Summarize", "Add to Search"],
                            value="Summarize",
                            show_label=False,
                            container=True,
                        )
                    with gr.Column(scale=1):
                        process_button = gr.Button(
                            "Process Video", scale=0, min_width=100
                        )

                process_result = gr.JSON(label="Result")

                # Bind the click event to the process_video function
                process_button.click(
                    fn=process_video,
                    inputs=[
                        camera_dropdown,
                        start_time_input,
                        end_time_input,
                        action_dropdown,
                    ],
                    outputs=process_result,
                )

            # Auto-Route Tab
            with gr.TabItem("Auto-Route Events to AI Search"):
                logger.info("Creating Auto-Route tab")

                with gr.Row():
                    with gr.Column(scale=2):
                        camera_dropdown = gr.Dropdown(
                            choices=camera_list,
                            label="Select Camera",
                            interactive=True,
                            container=True,
                        )

                    with gr.Column(scale=2):
                        label_filter = gr.Dropdown(
                            choices=["all", "person", "car", "animal"],
                            value="all",
                            label="Detection Labels",
                            container=True,
                        )

                    with gr.Column(scale=2):
                        action_dropdown_auto = gr.Dropdown(
                            choices=["Summarize", "Add to Search"],
                            value="Summarize",
                            label="Select Action",
                            container=True,
                        )

                    with gr.Column(scale=1):
                        process_auto_button = gr.Button(
                            "Add Rule", scale=0, min_width=100
                        )

        # Process button handler
        process_button.click(
            fn=lambda *args: (
                logger.info(f"Process button clicked with args: {args}"),
                process_video(*args),
            ),
            inputs=[camera_dropdown, start_time_input, end_time_input, action_dropdown],
            outputs=[process_result],
        )

        # Auto-route button handler
        process_auto_button.click(
            fn=lambda *args: (
                logger.info(f"Auto-route button clicked with args: {args}"),
                process_video(*args),
            ),
            inputs=[camera_dropdown, action_dropdown_auto, label_filter],
            outputs=[process_result],
        )

        # Initial load
        interface.load(fn=lambda: [], outputs=[events_table])

    logger.info("UI creation completed")
    return interface


if __name__ == "__main__":
    logger.info("=== Starting NVR Event Router UI ===")
    logger.info(f"API Base URL: {API_BASE_URL}")
    logger.info(f"Event Poll Interval: {EVENT_POLL_INTERVAL}s")

    try:
        start_time = time.time()
        initialize_app()
        init_time = time.time() - start_time
        logger.info(f"Initialization completed in {init_time:.2f}s")

        ui = create_ui()

        logger.info("Launching Gradio interface")
        ui.launch(server_name="0.0.0.0", show_error=True, favicon_path=None)
    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
    finally:
        logger.info("Application shutdown initiated")
        stop_event_updates()
        logger.info("=== Application shutdown complete ===")
