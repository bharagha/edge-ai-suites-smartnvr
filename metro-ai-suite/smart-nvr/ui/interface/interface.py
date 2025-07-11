import os
import gradio as gr
import threading
import tempfile
import time
import logging
from services.api_client import fetch_cameras, fetch_events, add_rule, fetch_rule_responses, fetch_rules, delete_rule_by_id, fetch_search_responses, fetch_summary_status
from services.video_processor import process_video
from services.event_utils import display_events
from config import logger
import json

camera_list = []
recent_events = []
# Global state
camera_list = []
recent_events = []
event_update_thread = None
stop_event_thread = threading.Event()

def initialize_app():
    """Initialize application and fetch initial data."""
    global camera_list
    logger.info("Initializing app and fetching camera list...")
    camera_list = fetch_cameras()
    return camera_list

def stop_event_updates():
    """Stop any background event polling."""
    global event_update_thread, stop_event_thread
    logger.info("Stopping event update thread...")
    if event_update_thread and event_update_thread.is_alive():
        stop_event_thread.set()
        event_update_thread.join(timeout=2)
        logger.info("Event update thread stopped.")

def cleanup_temp_files():
    """Clean up temporary MP4 files older than 1 hour."""
    logger.info("Cleaning up temp .mp4 files...")
    try:
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.endswith(".mp4"):
                full_path = os.path.join(temp_dir, file)
                age = time.time() - os.path.getmtime(full_path)
                if age > 3600:
                    os.remove(full_path)
                    logger.info(f"Deleted: {full_path}")
    except Exception as e:
        logger.error(f"Failed to clean temp files: {e}")

def render_rule_rows(rules, response_output):
    """Render rows of rules with delete buttons."""
    with gr.Column() as rule_column:
        for rule in rules:
            rule_id_state = gr.State(rule["id"])  # Hold rule ID as state

            with gr.Row():
                gr.Textbox(value=rule["id"], label="ID", interactive=False, show_label=False)
                gr.Textbox(value=rule.get("camera", ""), label="Camera", interactive=False, show_label=False)
                gr.Textbox(value=rule.get("label", ""), label="Label", interactive=False, show_label=False)
                gr.Textbox(value=rule.get("action", ""), label="Action", interactive=False, show_label=False)

                delete_btn = gr.Button("❌ Delete")
                delete_btn.click(
                    fn=delete_rule_by_id,
                    inputs=[rule_id_state],   # 👈 Pass the rule ID
                    outputs=[response_output]
                )
    return rule_column
polling_threads = {}

def poll_summary_status(summary_id, status_output, stop_event):
    while not stop_event.is_set():
        try:
            raw_response = fetch_summary_status(summary_id)

            # If the response is a JSON string, parse it
            if isinstance(raw_response, str):
                response = json.loads(raw_response)
            else:
                response = raw_response  # already a dict

            status = response.get("status", "unknown")
            logger.info(f"Polled summary {summary_id} status: {status}")
            status_output.update(value=f"Status: {status}")

            if status in ("completed", "failed"):
                break

        except Exception as e:
            logger.error(f"Error polling summary status: {e}", exc_info=True)
            status_output.update(value="Error fetching status")
            break

        time.sleep(10)
def process_and_poll(camera, start, duration, action, status_output):
    result = process_video(camera, start, duration, action)
    summary_id = result.get("summary_id")

    if result["status"] == "success" and summary_id:
        # Stop any previous polling
        if summary_id in polling_threads:
            polling_threads[summary_id]["stop"].set()

        stop_event = threading.Event()
        thread = threading.Thread(
            target=poll_summary_status,
            args=(summary_id, status_output, stop_event),
            daemon=True
        )
        thread.start()
        polling_threads[summary_id] = {"thread": thread, "stop": stop_event}

    return result
def create_ui():
    camera_list = fetch_cameras()
    recent_events = []
    def format_summary_responses():
        data = fetch_rule_responses()
        rows = []
        for rule_id, summaries in data.items():
            if summaries:
                for summary_id, message in summaries.items():
                    rows.append([rule_id, summary_id, message])
            else:
                rows.append([rule_id, "", "No summaries available."])
        return rows
    def format_search_responses():
        data = fetch_search_responses()
        rows = []
        for rule_id, results in data.items():
            if results:
                for item in results:
                    video_id = item.get("video_id", "")
                    message = item.get("message", "")
                    rows.append([rule_id, video_id, message])
            else:
                rows.append([rule_id, "", "No search results available."])
        return rows
    with gr.Blocks() as ui:
        gr.Markdown("## NVR Event Router")
        gr.Markdown("Monitor and process events from Frigate VMS using OEP Video Search and Summarization Application.")
        with gr.Tabs():
            # Tab 1: Summarize/Search
            with gr.TabItem("Summarize/Search Clips"):
                with gr.Row():
                    with gr.Column(scale=1):
                        cam_dropdown = gr.Dropdown(choices=camera_list, label="Select Camera")
                    with gr.Column(scale=1):
                        action_dropdown = gr.Dropdown(choices=["Summarize", "Add to Search"], value="Summarize")
                    with gr.Column(scale=1):
                        start_input = gr.DateTime(label="Start Time")
                    with gr.Column(scale=1):
                        duration_input = gr.Number(label="Duration (seconds)", precision=0)
                    with gr.Column(scale=1):
                        process_btn = gr.Button("Process Video")

                with gr.Row():
                    result = gr.JSON()
                    status_output = gr.Textbox(label="Summary Status", interactive=False)
                    status_state = gr.State("Waiting...")  # or just gr.State()
                process_btn.click(
                    fn=process_and_poll,
                    inputs=[cam_dropdown, start_input, duration_input, action_dropdown, status_state],
                    outputs=[result]
                )

            # Tab 2: AI-Powered Event Viewer
            with gr.TabItem("AI-Powered Event Viewer"):
                
                with gr.Row():
                    with gr.Column(scale=1):
                        cam_dropdown_view = gr.Dropdown(
                            choices=camera_list,
                            label="Select Camera",
                            interactive=True,
                            container=True
                        )
                    with gr.Column(scale=2):
                        gr.HTML("")  # Placeholder for spacing or future use
                with gr.Row():
                    with gr.Column(scale=2):
                        events_table = gr.Dataframe(
                            headers=["Label", "Start Time", "End Time", "Top Score", "Description", "Thumbnail"],
                            datatype=["str", "str", "str", "str", "str", "html"],
                            label="Events",
                            interactive=False,
                            elem_id="events-table",
                            elem_classes="events-table"
                        )
                        gr.HTML("""
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
                        """)


                def fetch_and_display_events(camera):
                    nonlocal recent_events
                    recent_events = fetch_events(camera)
                    return display_events(recent_events)

                cam_dropdown_view.change(fn=fetch_and_display_events, inputs=[cam_dropdown_view], outputs=[events_table])


            # Tab 3: Auto-Route Rules
            with gr.TabItem("Auto-Route Events to AI Search"):
                with gr.Row():
                    camera_dropdown = gr.Dropdown(choices=camera_list, label="Select Camera")
                    label_filter = gr.Dropdown(choices=["all", "person", "car", "animal"], value="all", label="Detection Labels")
                    action_dropdown_auto = gr.Dropdown(choices=["Summarize", "Add to Search"], value="Summarize", label="Select Action")
                    add_rule_alert = gr.Textbox(label="Status", visible=False)

                    gr.Button("➕ Add Rule").click(
                        fn=add_rule,
                        inputs=[camera_dropdown, label_filter, action_dropdown_auto],
                        outputs=[add_rule_alert]
                    )

                    # Optional: automatically show textbox when response is returned
                    def show_alert(resp: dict):
                        return resp.get("message", "No response"), gr.update(visible=True)

                    add_rule_alert.change(
                        fn=show_alert,
                        inputs=[add_rule_alert],
                        outputs=[add_rule_alert]
                    )

                gr.Markdown("### Current Rules")

                rules_table = gr.Dataframe(
                    headers=["ID", "Camera", "Label", "Action"],
                    datatype=["str", "str", "str", "str"],
                    interactive=False
                )

                def load_rules():
                    rules = fetch_rules()
                    return [[r["id"], r["camera"], r["label"], r["action"]] for r in rules]

                refresh_rules_btn = gr.Button("🔄 Refresh Rules")
                refresh_rules_btn.click(fn=load_rules, outputs=[rules_table])

                gr.Markdown("### Rule Responses")

                summary_response_table = gr.Dataframe(
                    headers=["Rule ID", "Summary ID", "Message"],
                    datatype=["str", "str", "str"],
                    label="Summary Responses",
                    interactive=False
                )

                gr.Button("🔄 Refresh Summary Responses").click(
                    fn=format_summary_responses,
                    outputs=[summary_response_table]
                )

                search_response_table = gr.Dataframe(
                    headers=["Rule ID", "Video ID", "Message"],
                    datatype=["str", "str", "str"],
                    label="Search Responses",
                    interactive=False
                )
                gr.Button("🔍 Refresh Search Responses").click(
                    fn=format_search_responses,
                    outputs=[search_response_table]
                )


                


    return ui

