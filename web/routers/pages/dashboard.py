import asyncio
import os

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

rootdir = os.getcwd()
template_dir = os.path.join(rootdir, "templates/dashboard")

router = APIRouter(prefix="/dashboard")
templates = Jinja2Templates(directory=template_dir)


@router.get("/")
async def index(request: Request):
    resp = await request.app.ipc.request("get_users_and_guilds")
    print(resp.response)

    return templates.TemplateResponse("index.html", {"request": request})
