from fastapi import APIRouter, Depends, HTTPException
from api.endpoints.frigate_api import FrigateService
from pydantic import BaseModel
from api.endpoints.summarization_api import SummarizationService
from service.vms_service import VmsService
from pydantic import BaseModel
from service import redis_store
from fastapi import Request

router = APIRouter()
frigate_service = FrigateService()
summarization_service = SummarizationService()
vms_service = VmsService(frigate_service, summarization_service)


@router.get("/cameras", summary="Get list of camera names")
async def get_cameras():
    return {"cameras": frigate_service.get_camera_names()}


@router.get(
    "/cameras/{camera_name}/clip",
    summary="Get video clip for specific camera and time range",
)
async def get_camera_clip(
    camera_name: str, start_time: float, end_time: float, download: bool = False
):
    return await frigate_service.get_camera_clip(
        camera_name, start_time, end_time, download
    )


@router.get("/events/{event_id}/clip.mp4", summary="Get event clip by event ID")
async def get_event_clip(event_id: str, download: bool = False):
    return await frigate_service.get_event_clip(event_id, download)


class ExportRequest(BaseModel):
    playback: str
    source: str
    name: str
    image_path: str


@router.post("/cameras/{camera_name}/export", summary="Export video from Frigate")
async def export_camera_clip(
    camera_name: str, start_time: float, end_time: float, request_data: ExportRequest
):
    return await frigate_service.export_camera_clip(
        camera_name, start_time, end_time, request_data.dict()
    )


@router.get("/exports/{export_id}", summary="Get details of a specific export")
async def get_export_details(export_id: str):
    return await frigate_service.get_export_details(export_id)


@router.get("/events", summary="Get list of events for a specific camera")
async def get_camera_events(camera: str):
    return await frigate_service.get_camera_events(camera)


@router.get("/exports/{export_id}/video", summary="Stream or download export video")
async def get_export_video(export_id: str, download: bool = False):
    return await frigate_service.stream_export_video(export_id, download)


@router.get("/summary/{camera_name}", summary="Stream video using clip.mp4 API")
async def summarize_video(
    camera_name: str, start_time: float, end_time: float, download: bool = False
):
    print("vms service")
    return await vms_service.summarize(camera_name, start_time, end_time)


@router.get(
    "/search-embeddings/{camera_name}", summary="Stream video using clip.mp4 API"
)
async def search_video_embeddings(
    camera_name: str, start_time: float, end_time: float, download: bool = False
):
    print("vms service search embeddings")
    return await vms_service.search_embeddings(camera_name, start_time, end_time)


@router.get("/summary-status/{summary_id}", summary="Get the summary using id")
async def get_summary(summary_id: str):
    return vms_service.summary(summary_id)


from service.redis_store import (
    get_rules,
    get_summary_ids,
    get_summary_result,
    get_search_results_by_rule,
)


@router.get("/rules/responses/")
async def get_all_rule_summaries(request: Request):
    rules = await get_rules(request)
    output = {}

    for rule in rules:
        rule_id = rule["id"]

        # Skip rules where the action contains "search"
        if "search" in rule.get("action", "").lower():
            continue

        summary_ids = await get_summary_ids(request, rule_id)
        summaries = {}

        for sid in summary_ids:
            result = vms_service.summary(sid)
            print(
                "result..............................................................................."
            )
            print(result)
            summaries[sid] = result or "Pending"

        output[rule_id] = summaries

    return output


@router.get("/rules/search-responses/")
async def get_search_responses(request: Request):
    """
    Fetch search responses for all rules with action 'search'.
    """
    output = {}

    try:
        rules = await get_rules(request)  # Fetch all rules

        for rule in rules:
            if rule.get("action") == "add to search":
                rule_id = rule["id"]
                results = await get_search_results_by_rule(rule_id, request)
                output[rule_id] = results or [{"status": "Pending"}]

        return output

    except Exception as e:
        return {"error": str(e)}


class Rule(BaseModel):
    id: str
    label: str
    action: str
    camera: str | None = None


@router.post("/rules/")
async def add_rule(rule: Rule, request: Request):
    success = await redis_store.add_rule(request, rule.id, rule.dict())
    if not success:
        raise HTTPException(status_code=400, detail="Rule ID already exists")
    return {"message": "Rule added", "rule": rule}


@router.get("/rules/")
async def list_rules(request: Request):
    return await redis_store.get_rules(request)


@router.get("/rules/{rule_id}")
async def get_rule(rule_id: str, request: Request):
    rule = await redis_store.get_rule(request, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str, request: Request):
    deleted = await redis_store.delete_rule(request, rule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": f"Rule {rule_id} deleted"}
