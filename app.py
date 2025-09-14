from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path
from routes.out1 import router as out1_router
from routes.status import router as status_router
from routes.misc import router as misc_router

app = FastAPI(title="HDMI Matrix Controller")
app.include_router(out1_router)
app.include_router(status_router)
app.include_router(misc_router)

@app.get("/")
def root(): return FileResponse(Path("static/index.html"))
