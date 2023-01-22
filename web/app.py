import asyncio
import importlib
import coloredlogs
import logging
import os

import uvicorn
from discord.ext.ipc import Client
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from dotenv import load_dotenv
load_dotenv()

debug = (
    True if not os.getenv("DEBUG") else False if os.getenv("DEBUG") == "false" else True
)

def intialize_ipc() -> Client:
    host = "bot" if not debug else "127.0.0.1"
    return Client(
        host=host,
        secret_key=os.getenv("IPC_SECRET_KEY")
    )
    
def setup_logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    dt_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(
        "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
    )

    filehandler = logging.handlers.RotatingFileHandler(
        filename="logs/web.log",
        encoding="utf-8",
        maxBytes=32 * 1024 * 1024,  # 32 MiB
        backupCount=5,  # Rotate through 5 files
    )
    filehandler.setFormatter(formatter)
    
    fmt = "%(name)s[%(process)d] %(levelname)s %(message)s"
    coloredlogs.install(logger=logger, fmt=fmt, level="DEBUG")
    logger.addHandler(filehandler)
    logger.setLevel(logging.DEBUG)

    return logger

app = FastAPI(debug=debug, docs_url=None, redoc_url=None)
app.ipc = intialize_ipc()
app.logger = setup_logger()
app.stats = {}

rootdir = os.getcwd()
template_dir = os.path.join(rootdir, "templates")
templates = Jinja2Templates(directory=template_dir)

app.mount("/static", StaticFiles(directory="static"), name="static")

async def update_statistics():
    connect_tries = 1
    while True:
        try:
            resp = await app.ipc.request("get_users_and_guilds")
            data = resp.response
            app.logger.debug(f"Updated stats: {data}")
            app.stats = data
            await asyncio.sleep(60)
        except ConnectionRefusedError:
            app.logger.error(f"Connection try #{connect_tries} failed")
            app.ipc = intialize_ipc()
            connect_tries += 1
            await asyncio.sleep(1)


@app.on_event("startup")
async def startup():
    asyncio.create_task(update_statistics())

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: Exception):
    status_code, detail = exc.status_code, exc.detail

    if status_code == 404:
        if request.url.path.startswith("/api"):
            return Response("Not found", status_code=404)
        return templates.TemplateResponse(
            "404.html", {"request": request}, status_code=404
        )

    return Response(f"{detail}, {status_code}", status_code=status_code)


rootdir = os.getcwd()
direc = os.path.join(rootdir, "routers")
for root, _, files in os.walk(direc):
    prefix = root[len(rootdir) + 1 :].replace(os.sep, ".")

    parent = prefix.split(".")[-1]  # get the parent of the file
    if parent == "__pycache__":  # ignore pycache folders
        continue

    for file in files:  # iterate through all files in a subdirectory
        fn = file[:-3]
        name = f"{prefix}.{fn}"
        imp = importlib.import_module(name)
        if hasattr(imp, "router"):
            app.include_router(getattr(imp, "router"))

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=5400, reload=debug)