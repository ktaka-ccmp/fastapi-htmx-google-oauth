from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from admin import debug, user, auth, admin
from htmx import htmx, htmx_secret, spa
from images import image

app = FastAPI(
    swagger_ui_parameters={"persistAuthorization": True},
    docs_url=None, redoc_url=None, openapi_url = None
    )

@app.exception_handler(auth.RequiresLogin)
async def requires_login(request: Request, _: Exception):
    return RedirectResponse(url="/spa/admin.login")

app.include_router(
    spa.router,
    prefix="/spa",
    tags=["spa"],
)

app.include_router(
    htmx.router,
    prefix="/htmx",
    tags=["htmx"],
)

app.include_router(
    htmx_secret.router,
    prefix="/htmx",
    tags=["htmx"],
    dependencies=[Depends(auth.is_authenticated)],
)

app.include_router(
    image.router,
    prefix="/img",
    tags=["Images"],
)

app.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

app.include_router(
    debug.router,
    prefix="/debug",
    tags=["Debug"],
    dependencies=[Depends(auth.is_authenticated)],
)

app.include_router(
    user.router,
    prefix="/crud",
    tags=["CRUD"],
    dependencies=[Depends(auth.is_authenticated)],
)

# docs and redocs
app.include_router(
    admin.doc_router,
    tags=["Admin"],
    include_in_schema=False,
    dependencies=[Depends(auth.is_authenticated_admin)]
)

# login endpoint for doc and redoc
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"],
    include_in_schema=False,
)

origins = [
    "http://localhost:3000",
    "http://v200.h.ccmp.jp:4000",
    ]

app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
