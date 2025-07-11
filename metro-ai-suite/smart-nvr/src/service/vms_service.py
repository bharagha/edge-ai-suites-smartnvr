import requests
import os
import tempfile
import subprocess
import aiofiles
import logging
from pathlib import Path
from typing import Optional
from fastapi import HTTPException
from api.endpoints.frigate_api import FrigateService
from model.model import Sampling, Evam, SummaryPayload
from api.endpoints.summarization_api import SummarizationService

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,  # Set to DEBUG if you want more verbose logs
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

frigate_service = FrigateService()
summarization_service = SummarizationService()

class VmsService:
    def __init__(self, frigate_service):
        self.frigate_service = frigate_service
        logger.info("VmsService initialized.")

    async def upload_video_to_summarizer(
        self,
        camera_name: str,
        start_time: float,
        end_time: float
    ) -> str:
        """Fetches clip from Frigate, writes to temp file, uploads it, and returns videoId."""
        try:
            stream_response = self.frigate_service.get_clip_from_timestamps(
                camera_name, start_time, end_time, download=True
            )
            logger.info("Clip retrieved from Frigate.")
        except Exception as e:
            logger.error(f"Failed to get clip: {e}")
            raise

        # Write stream to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_path = tmp_file.name
        logger.info(f"Temporary file created at: {tmp_path}")

        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                async for chunk in stream_response.body_iterator:
                    await f.write(chunk)
            logger.info("Stream written to temporary file.")
        except Exception as e:
            logger.error(f"Failed to write video stream to file: {e}")
            raise

        # Upload file
        try:
            upload_result = summarization_service.video_upload(tmp_path)
            logger.info(f"Video uploaded, videoId: {upload_result.get('videoId')}")
            return upload_result["videoId"]
        except Exception as e:
            logger.error(f"Video upload failed: {e}")
            raise
        finally:
            logger.info(f"You can view the saved video at: {tmp_path}")
            # Optional cleanup:
            # os.remove(tmp_path)

    
    async def summarize(
        self,
        camera_name: str,
        start_time: float,
        end_time: float
        ) -> str:
        logger.info(f"Starting summarization for camera: {camera_name}, "
                    f"start_time: {start_time}, end_time: {end_time}")

        try:
            video_id = await self.upload_video_to_summarizer(camera_name, start_time, end_time)
        except Exception as e:
            logger.error(f"Video processing/upload failed: {e}")
            raise

        try:
            payload = SummaryPayload(
                videoId=video_id,
                title="sample_summary_1",
                sampling=Sampling(chunkDuration=8, samplingFrame=3),
                evam=Evam(evamPipeline="object_detection")
            )
            pipeline = summarization_service.create_summary(payload)
            logger.info(f"Summary pipeline created with ID: {pipeline.get('summaryPipelineId')}")
            return pipeline["summaryPipelineId"]
        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
            raise

    
    def summary(self, summary_id: str):
        logger.info(f"Fetching summary result for ID: {summary_id}")
        try:
            result = summarization_service.get_summary_result(summary_id)
        except Exception as e:
            logger.error(f"Failed to retrieve summary: {e}")
            raise

        video_summary = result.get("summary")
        
        if not video_summary:
            logger.info("Summary not ready yet.")
            return "Summary is being generated please wait for a while and try again."
        
        logger.info("Summary retrieved successfully.")
        return video_summary
    async def search_embeddings(
        self,
        camera_name: str,
        start_time: float,
        end_time: float
    ) -> dict:
        """
        Uploads video from the specified camera and time range,
        then triggers the search-embeddings API.

        Returns:
            str: Message from the search-embeddings API response.
        """
        logger.info(f"Starting search_embeddings for camera={camera_name}, start={start_time}, end={end_time}")

        try:
            video_id = await self.upload_video_to_summarizer(camera_name, start_time, end_time)
        except Exception as e:
            logger.error(f"Failed to upload video for embedding search: {e}")
            raise

        url = f"{self.base_url}/manager/videos/search-embeddings/{video_id}"
        logger.info(f"Calling search-embeddings API: {url}")

        try:
            response = requests.post(url)
            response.raise_for_status()
            message = response.json().get("message", "No message in response.")
            logger.info(f"Embedding search response: {message}")
            return {video_id: message}
        except requests.RequestException as e:
            logger.error(f"Search embeddings API failed: {e}")
            raise
