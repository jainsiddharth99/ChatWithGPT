from fastapi.middleware.cors import CORSMiddleware

# origins = [
#     "http://localhost",
#     "http://localhost:3000",
#     "*"
# ]


def add_cors(app):
    """
    Adds cors
    """
    app.add_middleware(
        CORSMiddleware,
        # allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
