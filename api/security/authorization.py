from fastapi import Security, status, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.utils import decode_token
from database.database import samuraiUserToken

bearer = HTTPBearer()


async def authorization(
    credentials: HTTPAuthorizationCredentials = Security(bearer),
) -> dict:
    """
    Authorization check
    Checks wether Access token is valid
    """
    if credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_data = decode_token(credentials.credentials)
    token_in_database = samuraiUserToken.find_one(
        filter={"samurai_id": token_data["samurai_id"]}
    )
    if token_in_database is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is logged out",
        )
    #! uncomment it later for prod
    # if token_in_database["access_token"] == credentials.credentials:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Old Token",
    #     )

    return token_data


def get_user(credentials: dict = Depends(authorization)):
    """
    Returns current user
    """
    return credentials
