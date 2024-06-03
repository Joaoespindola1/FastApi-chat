from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import aioredis
import json

app = FastAPI()

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")


redis = aioredis.from_url("redis://localhost", decode_responses=True)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, websocket: WebSocket):
        self.active_connections.remove(websocket)
        for connection in self.active_connections:
            await connection.send_text(message)
        self.active_connections.append(websocket)

    async def save_message(self, room: str, message: str):
        await redis.rpush(room, message)

    async def get_messages(self, room: str):
        return await redis.lrange(room, 0, -1)


manager = ConnectionManager()

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("select_id.html", {"request": request})

@app.post("/chat")
async def post_chat(request: Request, client_id: str = Form(...)):
    messages = await manager.get_messages("chat_room")
    return templates.TemplateResponse("chat.html", {"request": request, "client_id": client_id, "messages": messages})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    message = f"{client_id} Entrou no chat"
    await manager.broadcast(message, websocket)
    await manager.save_message("chat_room", message)
    try:
        while True:
            data = await websocket.receive_text()
            message = f"{client_id}: {data}"
            await manager.send_personal_message(f"Você: {data}", websocket)
            await manager.broadcast(message, websocket)
            await manager.save_message("chat_room", message)
    except WebSocketDisconnect:
        message = f"{client_id} Saiu do chat"
        await manager.broadcast(message, websocket)
        manager.disconnect(websocket)
        await manager.save_message("chat_room", message)
