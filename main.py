from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()


templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

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


manager = ConnectionManager()

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("select_id.html", {"request": request})

@app.post("/chat")
async def post_chat(request: Request, client_id: str = Form(...)):
    return templates.TemplateResponse("chat.html", {"request": request, "client_id": client_id})

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.send_personal_message(f"Você: {data}", websocket)
            await manager.broadcast(f"{client_id}: {data}", websocket)
    except WebSocketDisconnect:
        await manager.broadcast(f"{client_id} Saiu do chat", websocket)
        manager.disconnect(websocket)
