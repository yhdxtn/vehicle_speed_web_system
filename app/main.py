from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.api.video_api import router as video_router
from app.api.line_api import router as line_router
from app.api.result_api import router as result_router

app = FastAPI(title="车辆速度跟踪与测速系统")

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "app" / "static")),
    name="static"
)

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

app.include_router(video_router)
app.include_router(line_router)
app.include_router(result_router)


@app.get("/")
def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "车辆速度跟踪与测速系统"
        }
    )