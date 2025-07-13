import requests
import logging
from fastapi import HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from typing import Optional
from pathlib import Path
from model.model import SummaryPayload
import os
import json
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,  # Change to logging.INFO to reduce verbosity
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

class SummarizationService:
    def __init__(self):
        logger.debug(f"SummarizationService initialized")

    def video_upload(self, video_path: str, base_url: str) -> dict:
        logger.debug(f"Starting video upload: {video_path}")

        video_path = Path(video_path)  # Ensure consistent use of Path
        if not video_path.is_file():
            logger.error(f"File does not exist at path: {video_path}")
            raise HTTPException(
                status_code=400,
                detail=f"Video file not found at path: {video_path}"
            )

        try:
            with open(video_path, "rb") as video_file:
                files = {
                    "video": (video_path.name, video_file, "video/mp4")
                }

                upload_url = f"{base_url}/manager/videos/"
                logger.debug(f"Sending POST request to {upload_url}")
                
                response = requests.post(
                    upload_url,
                    files=files,
                    timeout=30  # Optional: Add timeout
                )

            response.raise_for_status()
            logger.info(f"Video uploaded successfully: {video_path}")
            logger.debug(f"Upload response: {response.json()}")

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to upload video: {e}")
            if e.response is not None:
                logger.error(f"Status code: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to upload video: {str(e)}"
            )


    def create_summary(self, payload: SummaryPayload, base_url: str) -> dict:
        logger.debug(f"Creating summary for payload: {payload}")
        try:
            response = requests.post(
                f"{base_url}/manager/summary",
                json=payload.dict()
            )
            response.raise_for_status()
            logger.info("Summary creation request successful.")
            logger.debug(f"Summary creation response: {response.json()}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create summary: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to create summary: {str(e)}"
            )

    def get_summary_result(self, pipeline_id: str, base_url: str) -> dict:
        logger.debug(f"Fetching summary result for pipeline_id: {pipeline_id}")
        try:
            response = requests.get(f"{base_url}/manager/summary/{pipeline_id}")
            response.raise_for_status()

            json_data = response.json()
            logger.info(f"Summary result fetch successful for pipeline_id: {pipeline_id}")
            #logger.debug(f"Summary result JSON: {json.dumps(json_data, indent=2)}")

            return json_data  # ✅ This returns the full parsed response
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get summary result for pipeline_id {pipeline_id}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to get summary result: {str(e)}"
            )
