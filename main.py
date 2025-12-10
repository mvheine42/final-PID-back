# main.py
from dotenv import load_dotenv
load_dotenv()

import os, re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.responses import JSONResponse

from app.api import router

app = FastAPI()


ALLOWED_ORIGINS = [
    "http://localhost:4201",
    "http://localhost:3000",
    "https://two024-ranchoaparte-back.onrender.com",
    "https://2024-messidepaul-front.vercel.app",
    "https://2024-ranchoaparte-front-ivory.vercel.app",
    "http://2024-huidobro-front.vercel.app",
    "https://2024-huidobro-front-ey08brtzo-josehuidobro1s-projects.vercel.app",
    "https://final-pid-front-heine.vercel.app"
]

# Regex para Vercel extra si alguna vez lo necesitás
ALLOWED_ORIGIN_REGEX = r"^https://2024-.+\.vercel\.app$"

ALLOWED_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "X-Requested-With", "Accept", "Origin"]
EXPOSE_HEADERS = ["Authorization"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=ALLOWED_METHODS,
    allow_headers=ALLOWED_HEADERS,
    expose_headers=EXPOSE_HEADERS,
)

DEV_DEBUG = True
_origin_regex = re.compile(ALLOWED_ORIGIN_REGEX)

@app.middleware("http")
async def ensure_cors_on_errors(request, call_next):
    origin = request.headers.get("origin", "")
    try:
        response = await call_next(request)
    except HTTPException as http_exc:
        response = JSONResponse({"detail": http_exc.detail}, status_code=http_exc.status_code)
    except Exception as exc:
        if DEV_DEBUG:
            import traceback
            traceback.print_exc()
        response = JSONResponse({"detail": "Internal Server Error"}, status_code=500)

    if origin in ALLOWED_ORIGINS or _origin_regex.match(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"

    return response


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="C&V Bar API",
        version="1.0.0",
        description="Doc interactiva con JWT Firebase 🔐",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {"type": "http", "scheme": "bearer"}
    }

    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"HTTPBearer": []}])

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi


app.include_router(router)
