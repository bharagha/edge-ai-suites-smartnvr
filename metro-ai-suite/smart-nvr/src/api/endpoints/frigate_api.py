# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: Apache-2.0
import requests
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from fastapi.responses import FileResponse
import os
from pathlib import Path
from config import FRIGATE_BASE_URL


class FrigateService:
    def __init__(self, base_url: str = FRIGATE_BASE_URL):
        self.base_url = base_url

    def get_camera_names(self) -> list:
        """Get list of camera names from Frigate"""
        try:
            response = requests.get(f"{self.base_url}/api/config")
            response.raise_for_status()
            config = response.json()
            return list(config.get("cameras", {}).keys())
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to connect to Frigate: {str(e)}"
            )

    def get_camera_clip(
        self,
        camera_name: str,
        start_time: float,
        end_time: float,
        download: bool = False,
    ) -> StreamingResponse:
        """Get video clip from Frigate"""
        self._validate_time_range(start_time, end_time)

        url = f"{self.base_url}/api/{camera_name}/clip/{start_time}/{end_time}"
        if download:
            url += "?download=1"

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return StreamingResponse(
                response.iter_content(chunk_size=8192),
                media_type=response.headers["Content-Type"],
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", "inline"
                    )
                },
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="No clip found for specified time range"
                )
            raise

    @staticmethod
    def _validate_time_range(start_time: int, end_time: int):
        """Validate time range parameters"""
        if end_time <= start_time:
            raise HTTPException(
                status_code=400, detail="End time must be after start time"
            )
        if (end_time - start_time) > 300:  # 5 minute limit
            raise HTTPException(
                status_code=400, detail="Clip duration cannot exceed 300 seconds"
            )

    async def get_event_clip(
        self, event_id: str, download: bool = False
    ) -> StreamingResponse:
        """Fetch clip.mp4 for a specific event ID from Frigate"""
        url = f"{self.base_url}/api/events/{event_id}/clip.mp4"
        if download:
            url += "?download=1"

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return StreamingResponse(
                response.iter_content(chunk_size=8192),
                media_type=response.headers.get("Content-Type", "video/mp4"),
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", "inline"
                    )
                },
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail=f"Clip not found for event ID: {event_id}"
                )
            raise HTTPException(status_code=502, detail=f"Frigate error: {e}")
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to connect to Frigate: {str(e)}"
            )

    async def export_camera_clip(
        self, camera_name: str, start_time: float, end_time: float, payload: dict
    ) -> dict:
        """Trigger export of a video clip from Frigate"""
        self._validate_time_range(start_time, end_time)

        url = f"{self.base_url}/api/export/{camera_name}/start/{start_time}/end/{end_time}"

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Frigate export error: {e.response.text}",
            )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to contact Frigate: {str(e)}"
            )

    async def get_export_details(self, export_id: str) -> dict:
        """Get export metadata from Frigate"""
        url = f"{self.base_url}/api/exports/{export_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Frigate export lookup error: {e.response.text}",
            )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to contact Frigate: {str(e)}"
            )

    async def get_camera_events(self, camera_name: str) -> dict:
        """Get list of events for a specific camera"""
        url = f"{self.base_url}/api/events?camera={camera_name}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Frigate events API error: {e.response.text}",
            )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to contact Frigate: {str(e)}"
            )

    MEDIA_BASE_PATH = "/media/exports"

    async def stream_export_video(
        self, export_id: str, download: bool = False
    ) -> FileResponse:
        """Serve the export video file by export ID"""

        video_path = Path("/home/intel/frigate/media/exports") / f"{export_id}.mp4"
        video_path = video_path.as_posix()  # force forward-slash version
        print(f"[DEBUG] File exists: {os.path.exists(video_path)}")
        print(video_path)
        if not os.path.exists(video_path):
            raise HTTPException(
                status_code=404,
                detail=f"Video file not found for export ID: {export_id}",
            )

        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=f"{export_id}.mp4",
            headers={"Content-Disposition": "attachment" if download else "inline"},
        )

    def get_clip_from_timestamps(
        self, camera_name: str, start_time: int, end_time: int, download: bool = False
    ) -> StreamingResponse:
        """
        Call Frigate's /start/:start_ts/end/:end_ts/clip.mp4 API to retrieve a video clip.

        Args:
            camera_name (str): Name of the camera.
            start_time (int): Start timestamp (e.g. 1749531197).
            end_time (int): End timestamp (e.g. 1749531212).
            download (bool): If True, download the file.

        Returns:
            StreamingResponse: Video stream response.
        """
        if end_time <= start_time:
            raise HTTPException(
                status_code=400, detail="End time must be after start time"
            )

        url = f"{self.base_url}/api/{camera_name}/start/{start_time}/end/{end_time}/clip.mp4"
        if download:
            url += "?download=1"

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return StreamingResponse(
                response.iter_content(chunk_size=8192),
                media_type="video/mp4",
                headers={
                    "Content-Disposition": response.headers.get(
                        "Content-Disposition", "inline"
                    )
                },
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="Clip not found for specified time range"
                )
            raise HTTPException(
                status_code=502, detail=f"Frigate error: {e.response.text}"
            )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=502, detail=f"Failed to connect to Frigate: {str(e)}"
            )
