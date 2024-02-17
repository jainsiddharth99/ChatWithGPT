from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from middleware.cors import add_cors
from security.authorization import authorization
from routes.v1.auth.auth import router as Auth
from routes.v1.payments.payments import router as Payments
from routes.v1.openai.streaming import router as Streaming
from routes.v1.openai.completion import router as Completion
from routes.v1.user.user import router as UserData
from routes.v1.chat.chat import router as ChatRoute

app = FastAPI()
add_cors(app=app)


app.include_router(router=Streaming, prefix="/api/v1")
app.include_router(router=Completion, prefix="/api/v1")
app.include_router(router=Auth, prefix="/api/v1")
app.include_router(
    router=Payments, prefix="/api/v1", dependencies=[Depends(dependency=authorization)]
)
app.include_router(
    router=UserData, prefix="/api/v1", dependencies=[Depends(dependency=authorization)]
)
app.include_router(
    router=ChatRoute,
    prefix="/api/v1",
    dependencies=[Depends(dependency=authorization)],
)


@app.get("/api/v1")
def home():
    """
    Test API Connection
    """
    html_content = """
    <html>
        <head>
            <title>Samurai</title>
        </head>
        <body>
            <h1>🗡️Samurai🗡</h1>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


@app.exception_handler(HTTPException)
async def http_exception_handler(_, exc) -> JSONResponse:
    """
    Error handling
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
