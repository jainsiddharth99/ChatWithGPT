import shutil
import os
from urllib import response
from fastapi import APIRouter, status, Depends, Response
from models.payload import UserSchema, CompleteUser
from security.authorization import get_user
from exceptions.exceptions import (
    account_does_not_exist_error,
    incorrect_business_error,
)
from helper.utils import get_time
from database.database import samuraiUser
from config.settings import settings
from config.file_upload import upload_file

router = APIRouter()


@router.get(
    path="/user/get-user",
    status_code=status.HTTP_200_OK,
    summary="USER DETAILS",
    response_model=UserSchema,
)
def get_user_details(current_user=Depends(get_user)):
    """
    Returns user details
    """
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    if db_user is None:
        account_does_not_exist_error()
    return db_user


@router.post(
    path="/user/profile/",
    status_code=status.HTTP_200_OK,
    summary="user profile completed",
)
def complete_user_profile(
    response: Response,
    payload: CompleteUser = Depends(),
    current_user=Depends(get_user),
):
    """
    Returns user details
    """
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    if db_user is None:
        account_does_not_exist_error()
    if db_user["profile_completed"] is not True:
        update_query = {
            "$inc": {
                "subscription.free_queries": int(settings["CREDITS_PROFILE_COMPLETION"])
            }
        }
        response_type = "COMPLETED"
        status_code = status.HTTP_200_OK
    else:
        update_query, response_type = {}, "UPDATED"
        status_code = status.HTTP_202_ACCEPTED
        response.status_code = status.HTTP_202_ACCEPTED

    if payload.account_type.lower() not in ["business", "team", "student"]:
        incorrect_business_error()
    with open(payload.profile_picture.filename, "wb+") as buffer:
        shutil.copyfileobj(payload.profile_picture.file, buffer)
    image_link = upload_file("profile_pictures", payload.profile_picture.filename)
    update_query["$set"] = {
        "profile_completed": True,
        "name": payload.name,
        "email": payload.email,
        "account_type": payload.account_type,
        "profile_picture": image_link,
        "updated_at": get_time(),
    }
    samuraiUser.update_one(
        filter={"samurai_id": current_user["samurai_id"]},
        update=update_query,
    )
    os.remove(payload.profile_picture.filename)
    return {
        "status_code": status_code,
        "response_type": "SUCCESS",
        "description": f"USER PROFILE {response_type}",
    }
