from pathlib import Path

from fastapi import FastAPI
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

WEBAPP_MOUNT_PATH = "/app"


class SpaStaticFiles(StaticFiles):
    """Static files with a client-side-routing fallback.

    The cabinet uses history routing, so a reload on `/app/devices` asks the
    server for a file that does not exist. Anything missing that is not a build
    asset is answered with `index.html` and resolved by the router in the
    browser.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exception:
            if exception.status_code != 404:
                raise
            # A missing hashed asset is a genuine 404 — serving HTML in its
            # place would only surface as a confusing MIME error.
            if path.startswith("assets/"):
                raise
            return await super().get_response("index.html", scope)


def mount_webapp(app: FastAPI, directory: Path) -> bool:
    """Mount the built Mini App if it is present.

    Returns whether it was mounted. A missing build is not fatal: the API is
    useful on its own, and the image can be built without the frontend stage.
    """
    if not (directory / "index.html").is_file():
        logger.warning(
            f"Mini App build not found at '{directory}', skipping mount. "
            f"Run 'npm ci && npm run build' in webapp/ to enable it."
        )
        return False

    app.mount(
        WEBAPP_MOUNT_PATH,
        SpaStaticFiles(directory=directory, html=True),
        name="webapp",
    )
    logger.info(f"Mini App mounted at '{WEBAPP_MOUNT_PATH}' from '{directory}'")
    return True
