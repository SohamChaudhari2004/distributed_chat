import sys
import os
import grpc.aio
from fastapi import FastAPI, WebSocket, HTTPException, Depends, Body
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import json
import asyncio

class AuthRequest(BaseModel):
    username: str
    password: str

sys.path.append(os.path.dirname(__file__))

import pb.auth_pb2 as auth_pb2
import pb.auth_pb2_grpc as auth_pb2_grpc
import pb.store_pb2 as store_pb2
import pb.store_pb2_grpc as store_pb2_grpc
import pb.chat_pb2 as chat_pb2
import pb.chat_pb2_grpc as chat_pb2_grpc

app = FastAPI()

AUTH_HOST = os.environ.get("AUTH_HOST", "localhost:50051")
STORE_HOST = os.environ.get("STORE_HOST", "localhost:50052")
CHAT_HOST = os.environ.get("CHAT_HOST", "localhost:50053")

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
def read_index():
    with open(os.path.join(static_dir, "index.html"), "r") as f:
        return HTMLResponse(f.read())

@app.post("/register")
async def register(req: AuthRequest):
    async with grpc.aio.insecure_channel(AUTH_HOST) as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        try:
            resp = await stub.Register(auth_pb2.RegisterRequest(username=req.username, password=req.password))
            if resp.success:
                return {"success": True}
            else:
                raise HTTPException(status_code=400, detail=resp.message)
        except grpc.aio.AioRpcError as e:
            raise HTTPException(status_code=500, detail=str(e.details()))

@app.post("/login")
async def login(req: AuthRequest):
    async with grpc.aio.insecure_channel(AUTH_HOST) as channel:
        stub = auth_pb2_grpc.AuthServiceStub(channel)
        try:
            resp = await stub.Login(auth_pb2.LoginRequest(username=req.username, password=req.password))
            if resp.success:
                return {"success": True}
            else:
                raise HTTPException(status_code=400, detail=resp.message)
        except grpc.aio.AioRpcError as e:
            raise HTTPException(status_code=500, detail=str(e.details()))

@app.get("/history")
async def history():
    async with grpc.aio.insecure_channel(STORE_HOST) as channel:
        stub = store_pb2_grpc.StoreServiceStub(channel)
        try:
            resp = await stub.GetHistory(store_pb2.GetHistoryRequest(limit=50))
            return {"messages": [{"sender": m.sender, "message": m.message, "timestamp": m.timestamp} for m in resp.messages]}
        except grpc.aio.AioRpcError as e:
            raise HTTPException(status_code=500, detail=str(e.details()))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        token = await websocket.receive_text()  # Client sends basic auth token first
    except Exception:
        return
    
    import base64
    try:
        decoded = base64.b64decode(token).decode()
        username = decoded.split(':')[0]
    except:
        username = "unknown"
    
    print(f"[{username}] WebSocket opened with token: {token[:20]}...")
    
    metadata = (('authorization', f'Basic {token}'),)
    last_activity = asyncio.get_event_loop().time()
    inactivity_timeout = 300  # 5 minutes in seconds
    
    async with grpc.aio.insecure_channel(CHAT_HOST) as channel:
        stub = chat_pb2_grpc.ChatServiceStub(channel)
        call = stub.ChatStream(metadata=metadata)
        connection_active = True
        write_closed = False
        
        async def read_ws_write_grpc():
            nonlocal last_activity, connection_active, write_closed
            try:
                while connection_active:
                    try:
                        data = await asyncio.wait_for(websocket.receive_text(), timeout=inactivity_timeout)
                        last_activity = asyncio.get_event_loop().time()
                        print(f"[{username}] Sending to gRPC: {data}")
                        await call.write(chat_pb2.ChatMessage(message=data))
                        print(f"[{username}] Written to gRPC stream successfully")
                    except asyncio.TimeoutError:
                        # 5 minutes of inactivity - close connection
                        print(f"[{username}] Inactivity timeout (5 min)")
                        connection_active = False
                        break
            except Exception as e:
                print(f"[{username}] WS read error: {e}")
                connection_active = False
            finally:
                write_closed = True
                print(f"[{username}] read_ws_write_grpc task finished")

        async def read_grpc_write_ws():
            nonlocal last_activity, connection_active
            try:
                print(f"[{username}] Starting to read from gRPC stream")
                async for resp in call:
                    if not connection_active:
                        print(f"[{username}] connection_active is False, breaking read loop")
                        break
                    last_activity = asyncio.get_event_loop().time()
                    msg_text = json.dumps({
                        "sender": resp.sender,
                        "message": resp.message,
                        "timestamp": resp.timestamp
                    })
                    print(f"[{username}] Received from gRPC: {resp.sender} - {resp.message}")
                    await websocket.send_text(msg_text)
                    print(f"[{username}] Sent to WebSocket: {msg_text[:50]}...")
            except asyncio.CancelledError:
                print(f"[{username}] gRPC read task was cancelled")
            except Exception as e:
                print(f"[{username}] GRPC read error: {type(e).__name__}: {str(e)[:100]}")
                connection_active = False
            finally:
                print(f"[{username}] read_grpc_write_ws task finished")
        
        # Close the write side after read_ws_write_grpc finishes
        async def close_write_when_done():
            await read_ws_write_grpc()
            print(f"[{username}] Closing gRPC write side")
            await call.done_writing()
                
        task1 = asyncio.create_task(close_write_when_done())
        task2 = asyncio.create_task(read_grpc_write_ws())
        
        print(f"[{username}] Tasks created, waiting for both to complete...")
        await asyncio.gather(task1, task2, return_exceptions=True)
        print(f"[{username}] WebSocket closed")
