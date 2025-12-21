import json
import asyncio
import logging
import websockets
from Backend.api.auth import verify_websocket_token
from Backend.api.database import get_db , sessionLocal
from Backend.api import models
from Backend.api.websocket.redis_cancel import request_cancel
from Backend.api.websocket.chat_agent import stream_chat
from Backend.api.routers.ingestion.status import get_status
from sqlalchemy.orm import Session




logger = logging.getLogger("ws_server")




class WSContext:
    def __init__(self, user_id, user_name, thread_id):
        self.user_id = user_id
        self.user_name = user_name
        self.thread_id = thread_id
        self.file_ids = []


def check_thread_ownership(user_id: int, thread_id: str) -> bool:
    db = next(get_db())
    return db.query(models.Thread).filter(
        models.Thread.uuid == thread_id,
        models.Thread.admin_id == user_id
    ).first() is not None


def retrieve_file_ids_for_thread(thread_id: str, db: Session):
    # Get the thread's integer ID from its UUID
    thread = db.query(models.Thread).filter(models.Thread.uuid == thread_id).first()
    if not thread:
        return []
    
    return [
        row.file_uuid
        for row in db.query(models.UploadedFiles.file_uuid)
        .filter(models.UploadedFiles.thread_id == thread.id)
        .all()
    ]


def retrieve_file_ids_for_thread_db(thread_id: str):
    db = sessionLocal()
    try:
        file_ids = retrieve_file_ids_for_thread(thread_id, db)
        if not file_ids:
            return []
        return file_ids
    finally:
        db.close()


    


async def handle_client(ws):
    """Handle WebSocket client connection with proper error handling."""
    context = None
    user_id = None
    user_name = None
    
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await ws.send(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            action = data.get("action")

            # ===== AUTH =====
            if action == "auth":
                token = data.get("token")
                user_data = verify_websocket_token(token)
                if not user_data:
                    await ws.send(json.dumps({"type": "error", "message": "Auth failed"}))
                    return

                user_id = user_data["user_id"]
                user_name = user_data["user_name"]

                await ws.send(json.dumps({
                    "type": "auth_ok",
                    "user_id": user_id,
                    "username": user_name
                }))

            # ===== SET THREAD =====
            elif action == "set_thread":
                thread_id = data.get("thread_id")
                file_ids =  retrieve_file_ids_for_thread_db(thread_id) 

                if not check_thread_ownership(user_id, thread_id):
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "Invalid thread"
                    }))
                    continue

                context = {
                    "thread_id": thread_id,
                    "file_ids": file_ids,
                    "user_id": str(user_id),  # Convert to string for Context
                    "user_name": user_name
                }

                await ws.send(json.dumps({
                    "type": "thread_ok",
                    "thread_id": thread_id,
                    "file_ids": file_ids
                }))

            #===== ADD FILE =====
            elif action == "add_file":
                file_id = data.get("file_id")

                if not context:
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "Thread not initialized"
                  }))
                    continue
                context["file_ids"].append(file_id)

                await ws.send(json.dumps({
                    "type": "file_added",
                    "file_id": file_id
                }))

            # ===== CHAT =====
            elif action == "chat":
                if not context:
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "Thread not initialized"
                    }))
                    continue

                message = data.get("message")
                show_tools_responses = data.get("show_tools_responses", False)

                async for chunk in stream_chat(
                    thread_id=context["thread_id"],
                    user_id=context["user_id"],
                    user_name=context["user_name"],
                    message=message,
                    file_ids=context["file_ids"],
                    show_tools_responses=show_tools_responses
                ):
                    await ws.send(json.dumps(chunk))
                    
            # ===== STATUS =====
            elif action == "watch_ingestion":
                job_id = data.get("job_id")
                print(f"Starting to watch ingestion for job_id: {job_id}")

                if not job_id:
                    await ws.send(json.dumps({
                        "type": "error",
                        "message": "job_id required"
                    }))
                    continue

                while True:
                    status = await get_status(job_id)
                    print(f"Status for job {job_id}: {status}")

                    if not status:
                        print(f"Job {job_id} not found in Redis")
                        await ws.send(json.dumps({
                            "type": "error",
                            "message": "Job not found"
                        }))
                        break

                    response = {
                        "type": "ingestion_status",
                        "job_id": job_id,
                        "state": status["state"],
                        "progress": status.get("progress", 0),
                        "file_id": status.get("file_id"),
                        "thread_id": status.get("thread_id"),
                    }
                    print(f"Sending status update: {response}")
                    await ws.send(json.dumps(response))

                    if status["state"] in ("completed", "failed"):
                        print(f"Job {job_id} finished with state: {status['state']}")
                        break

                    await asyncio.sleep(1)

            # ===== CANCEL =====
            elif action == "cancel":
                if context:
                    await request_cancel(context["thread_id"])

            # ===== UNKNOWN =====
            else:
                await ws.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown action: {action}"
                }))
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        try:
            await ws.send(json.dumps({"type": "error", "message": "Invalid JSON format"}))
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await ws.send(json.dumps({"type": "error", "message": "Internal server error"}))
        except Exception:
            pass
    finally:
        if user_id and context:
            logger.info(f"Client disconnected: user_id={user_id}, thread_id={context.get('thread_id')}")


async def start_websocket_server(host="0.0.0.0", port=8071):
    async with websockets.serve(handle_client, host, port):
        logger.info(f"WebSocket running on ws://{host}:{port}")
        await asyncio.Future()




