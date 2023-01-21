import os

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

rootdir = os.getcwd()
template_dir = os.path.join(rootdir, "templates")

router = APIRouter(prefix="")
templates = Jinja2Templates(directory=template_dir)


@router.get("/")
async def index(request: Request):
    data = request.app.stats

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "users": data.get("users", 0),
            "guilds": data.get("guilds", 0),
        },
    )
