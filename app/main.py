from fastapi import FastAPI
from fastapi.responses import JSONResponse
import time
import json
from datetime import datetime
from fastapi import Query
from app.core.cache import cache
from app.services.loader import load_all
from app.services.poi_distance import find_nearby_pois
from app.vectorstore.policy_index import build_all_indexes, search_policy
from app.utils.json_safe import json_safe
import logging
from app.middleware.timing import timing_middleware
from app.api.ask import router as ask_router
from app.api.call import router as call_router
from fastapi.staticfiles import StaticFiles
from app.services.llm_factory import get_llm_factory
from app.services.tts.elevenlabs_client import ElevenLabsClient
import base64
import uuid

logging.basicConfig(level=logging.INFO)


app = FastAPI(title="MP Industrial Agent Backend")
app.include_router(ask_router)
app.include_router(call_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.middleware("http")(timing_middleware)

@app.on_event("startup")
def startup():
    load_all()
    build_all_indexes()
    cache["last_updated"] = datetime.utcnow().isoformat()

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "states": list(cache["states"].keys()),
        "lastUpdated": cache["last_updated"]
    }

@app.get("/api/{state}/parks")
def parks(
    state: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    t0 = time.perf_counter()

    all_parks = cache["states"].get(state, {}).get("parks", [])
    total = len(all_parks)

    t1 = time.perf_counter()

    sliced = all_parks[offset : offset + limit]
    safe_parks = json_safe(sliced)

    t2 = time.perf_counter()

    payload_size_kb = len(
        json.dumps(safe_parks, default=str).encode("utf-8")
    ) / 1024

    print(
        f"[DEBUG][parks] state={state} "
        f"total={total} returned={len(safe_parks)} "
        f"limit={limit} offset={offset} | "
        f"fetch={(t1 - t0)*1000:.2f} ms | "
        f"slice+sanitize={(t2 - t1)*1000:.2f} ms | "
        f"payload={payload_size_kb:.1f} KB"
    )

    return {
        "meta": {
            "total": total,
            "returned": len(safe_parks),
            "limit": limit,
            "offset": offset
        },
        "data": safe_parks
    }


@app.get("/api/{state}/plots")
def plots(
    state: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    t0 = time.perf_counter()

    all_plots = cache["states"].get(state, {}).get("plots", [])
    total = len(all_plots)

    t1 = time.perf_counter()

    sliced = all_plots[offset : offset + limit]
    safe_plots = json_safe(sliced)

    t2 = time.perf_counter()

    payload_size_kb = len(
        json.dumps(safe_plots, default=str).encode("utf-8")
    ) / 1024

    print(
        f"[DEBUG][plots] state={state} "
        f"total={total} returned={len(safe_plots)} "
        f"limit={limit} offset={offset} | "
        f"fetch={(t1 - t0)*1000:.2f} ms | "
        f"slice+sanitize={(t2 - t1)*1000:.2f} ms | "
        f"payload={payload_size_kb:.1f} KB"
    )

    return {
        "meta": {
            "total": total,
            "returned": len(safe_plots),
            "limit": limit,
            "offset": offset
        },
        "data": safe_plots
    }

@app.get("/api/{state}/pois")
def pois(state: str):
    return json_safe(cache["states"].get(state, {}).get("pois", []))


@app.get("/api/{state}/policy/search")
def policy_search(state: str, q: str):
    return search_policy(q, state)

@app.get("/api/{state}/pois/nearby")
def pois_nearby(
    state: str,
    lat: float,
    lng: float,
    radius_km: float = 10,
    poi_type: str | None = None
):
    return find_nearby_pois(state, lat, lng, radius_km, poi_type)

@app.post("/api/ask/voice")
def ask_with_voice(payload: dict):
    """
    Voice conversation endpoint with dual-response mode.
    
    Returns:
    {
        "text_response": "Long structured response for chat UI",
        "voice_response": "Short 2-4 sentence response for TTS",
        "audio_base64": "Base64-encoded MP3 audio",
        "conversation_state": {...},
        "model": "model name",
        "turn_number": "which turn in conversation",
        "warnings": [...],
    }
    """
    question = payload.get("question")
    conversation_state = payload.get("conversation_state", {})  # Optional context from frontend
    state = payload.get("state", "madhya_pradesh")  # Default state
    
    if not question:
        return JSONResponse(status_code=400, content={"error": "Question required"})

    llm = get_llm_factory()
    
    try:
        tts = ElevenLabsClient()
    except Exception as e:
        logging.error(f"TTS Client Init Error: {e}")
        tts = None

    # 1. Retrieve relevant data (existing logic)
    try:
        from app.agents.agent import _execute_tools_intelligently
        from app.core.observability import RequestLogger, get_performance_monitor
        
        request_logger = RequestLogger("voice_" + str(uuid.uuid4())[:8])
        perf_monitor = get_performance_monitor()
        
        retrieved_data = _execute_tools_intelligently(
            state,
            question,
            request_logger,
            perf_monitor
        )
    except Exception as e:
        logging.error(f"Tool execution error: {e}")
        retrieved_data = {
            "policies": [],
            "parks": [],
            "plots": [],
            "pois": []
        }

    # 2. Generate DUAL responses (text + voice) in single LLM call
    llm_response = llm.generate_dual_response(
        question=question,
        context_data=retrieved_data,
        conversation_context=conversation_state,
    )
    
    if llm_response.get("status") == "error":
        return JSONResponse(
            status_code=500,
            content={"error": llm_response.get("error", "LLM Error")}
        )

    text_response = llm_response.get("text_response", "")
    voice_response = llm_response.get("voice_response", "")
    conversation_state_updated = llm_response.get("conversation_state", {})

    # 3. Convert voice response to audio
    audio_base64 = None
    if tts and voice_response:
        try:
            audio_bytes = tts.synthesize(voice_response)
            if audio_bytes:
                audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        except Exception as e:
            logging.error(f"TTS Synthesis Error: {e}")
            # Proceed without audio

    return {
        "text_response": text_response,
        "voice_response": voice_response,
        "audio_base64": audio_base64,
        "conversation_state": conversation_state_updated,
        "model": llm_response.get("model", "unknown"),
        "provider": llm_response.get("provider", "unknown"),
        "turn_number": conversation_state.get("turn_number", 1) + 1,
        "warnings": llm_response.get("warnings", []),
    }