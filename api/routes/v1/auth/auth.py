from uuid import uuid4
from fastapi import APIRouter, status, Depends
from config.settings import settings
from security.authorization import get_user
from models.payload import (
    SignUpSchema,
    DeviceSignUp,
    LoginSchema,
    UserOut,
    TokenSchema,
    OTP,
    ResendEmailOTP,
    ForgetPassword,
)
from helper.utils import get_time
from utils.utils import (
    get_secret_key_otp,
    get_current_otp,
    get_hashed_password,
    send_email_otp,
    verify_password,
    create_access_token,
    create_customer,
)
from exceptions.exceptions import (
    account_exists_error,
    account_does_not_exist_error,
    password_does_not_match_error,
    password_length_error,
    incorrect_password_error,
    wrong_otp_error,
    account_not_verified_error,
)
from database.database import (
    samuraiUser,
    samuraiUserToken,
    samuraiUserHistory,
    samuraiDeletedUser,
)


router = APIRouter()


@router.post(
    path="/auth/signup",
    status_code=status.HTTP_201_CREATED,
    summary="SignUp user Samurai",
    response_model=UserOut,
)
def signup(payload: SignUpSchema) -> UserOut:
    """
    The `signup` function creates a new user account by validating the input payload, hashing the
    password, generating a unique ID and OTP secret, creating a customer in Stripe, and sending an email
    with the OTP.

    Args:
      payload (SignUpSchema): The `payload` parameter is an instance of the `SignUpSchema` class. It
    contains the data needed to create a new user account.

    Returns:
      the `payload` object.
    """
    if samuraiUser.find_one(filter={"email": payload.email}) is not None:
        account_exists_error()
    if payload.password != payload.confirm_password:
        password_does_not_match_error()
    if len(payload.password) < 8 or len(payload.password) > 16:
        password_length_error()
    payload.password = get_hashed_password(payload.password)
    del payload.confirm_password
    payload.samurai_id = str(uuid4())
    payload.otp_secret = get_secret_key_otp()
    payload.created_at = get_time()
    payload.updated_at = get_time()
    payload.stripe_id = create_customer(payload.name, payload.email)
    payload.verified = False
    payload.subscription = {"type": "TRIAL", "active": False, "free_queries": 5}
    samuraiUser.insert_one(document=payload.dict())
    current_otp = get_current_otp(payload.otp_secret)
    send_email_otp(payload.email, current_otp.now())
    return payload


@router.post(
    path="/auth/device/signup",
    status_code=status.HTTP_201_CREATED,
    summary="Device SignUp user Samurai",
)
def device_signup(payload: DeviceSignUp):
    user = samuraiUser.find_one({"device_id": payload.device_id})
    if user is None:
        payload.samurai_id = str(uuid4())
        payload.otp_secret = get_secret_key_otp()
        payload.created_at = get_time()
        payload.updated_at = get_time()
        payload.verified = False
        payload.subscription = {
            "type": "TRIAL",
            "active": False,
            "free_queries": int(settings["CREDITS_NEW_USER"]),
        }
        samuraiUser.insert_one(document=payload.dict())
        samurai_id = payload.samurai_id
    else:
        samurai_id = user["samurai_id"]
    token = {"access_token": create_access_token(samurai_id, 365)}
    samuraiUserToken.update_one(
        {"samurai_id": samurai_id}, {"$set": token}, upsert=True
    )
    return token


@router.post(
    path="/auth/device/login",
    status_code=status.HTTP_201_CREATED,
    summary="Device login user Samurai",
)
def device_login(payload: DeviceSignUp):
    db_user = samuraiUser.find_one({"device_id": payload.device_id})
    if db_user is None:
        account_does_not_exist_error()
    token = {"access_token": create_access_token(db_user["samurai_id"])}
    samuraiUserToken.update_one({"samurai_id": db_user["samurai_id"]}, {"$set": token})
    return token


@router.post(
    path="/auth/login",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Login user Samurai",
    response_model=TokenSchema,
)
def login(payload: LoginSchema):
    """
    The `login` function checks if a user exists in the database, verifies their password, and sends an
    OTP email if the account is not verified, then returns an access token.

    Args:
      payload (LoginSchema): The `payload` parameter is of type `LoginSchema`. It represents the data
    needed for a user to log in. The `LoginSchema` could be a data structure or a class that contains
    the following properties:

    Returns:
      a token, which is a dictionary containing an access_token.
    """
    db_user = samuraiUser.find_one({"email": payload.email})
    if db_user is None:
        account_does_not_exist_error()
    if not verify_password(payload.password, db_user["password"]):
        incorrect_password_error()
    if db_user["verified"] is False:
        current_otp = get_current_otp(db_user["otp_secret"])
        send_email_otp(payload.email, current_otp.now())
        account_not_verified_error()

    token = {"access_token": create_access_token(db_user["samurai_id"])}
    samuraiUserToken.update_one(
        {"samurai_id": db_user["samurai_id"]}, {"$set": token}, upsert=True
    )
    return token


@router.post(
    path="/auth/verification",
    status_code=status.HTTP_202_ACCEPTED,
    summary="OTP validation",
    response_model=TokenSchema,
)
def verification(payload: OTP):
    """
    The function `verification` verifies the OTP provided by the user and updates the user's verification
    status in the database, generates an access token, and logs the user's history.

    Args:
      payload (OTP): The `payload` parameter is an object of type `OTP`.

    Returns:
      a token, which is a dictionary containing the samurai_id and access_token.
    """
    db_user = samuraiUser.find_one({"email": payload.email})
    if db_user is None:
        account_does_not_exist_error()
    otp_secret_key = db_user["otp_secret"]
    current_otp = get_current_otp(otp_secret_key)

    if current_otp.verify(payload.otp) is False:
        wrong_otp_error()
    samuraiUser.update_one(
        filter={"samurai_id": db_user["samurai_id"]},
        update={"$set": {"verified": True, "updated_at": get_time()}},
    )
    token = {
        "samurai_id": db_user["samurai_id"],
        "access_token": create_access_token(db_user["samurai_id"]),
    }
    samuraiUserToken.insert_one(token)
    samuraiUserHistory.insert_one({"samurai_id": db_user["samurai_id"]})

    return token


@router.post(
    path="/auth/resend-otp", status_code=status.HTTP_200_OK, summary="Resend OTP"
)
def resend_otp(payload: ResendEmailOTP):
    """
    The function `resend_otp` resends an OTP (One-Time Password) to the user's email address.

    Args:
      payload (ResendEmailOTP): The payload parameter is an object of type ResendEmailOTP. It contains
    the email address of the user for whom the OTP needs to be resent.

    Returns:
      a dictionary with the following keys and values:
    - "status_code": status.HTTP_200_OK
    - "response_type": "SUCCESS"
    - "description": "OTP Sent"
    """
    db_user = samuraiUser.find_one({"email": payload.email})
    if db_user is None:
        account_does_not_exist_error()
    otp_secret_key = db_user["otp_secret"]
    current_otp = get_current_otp(otp_secret_key)
    send_email_otp(payload.email, current_otp.now())
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "OTP Sent",
    }


@router.post(
    path="/auth/password-reset",
    status_code=status.HTTP_201_CREATED,
    summary="Forget Password",
)
def reset_password(payload: ForgetPassword):
    """
    The `reset_password` function is used to change a user's password if they have forgotten it, by verifying
    their OTP and updating their password in the database.

    Args:
      payload (ForgetPassword): The `payload` parameter is an object of type `ForgetPassword`. It
    contains the following attributes:

    Returns:
      a dictionary with the following keys and values:
    - "status_code": status.HTTP_201_CREATED
    - "response_type": "SUCCESS"
    - "description": "Password Changed"
    """
    if payload.new_password != payload.confirm_new_password:
        password_does_not_match_error()
    if len(payload.new_password) < 8 or len(payload.new_password) > 16:
        password_length_error()
    db_user = samuraiUser.find_one({"email": payload.email})
    if db_user is None:
        account_does_not_exist_error()
    otp_secret_key = db_user["otp_secret"]
    current_otp = get_current_otp(otp_secret_key)

    if current_otp.verify(payload.otp) is False:
        wrong_otp_error()
    payload.new_password = get_hashed_password(payload.new_password)
    samuraiUser.update_one(
        {"email": db_user["email"]},
        {"$set": {"password": payload.new_password, "updated_at": get_time()}},
    )

    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": "Password Changed",
    }


@router.post(
    path="/auth/logout",
    status_code=status.HTTP_200_OK,
    summary="user logout",
)
def user_logout(current_user=Depends(get_user)):
    """
    The function `user_logout` logs out the current user by deleting their token from the database.

    Args:
      current_user: The current_user parameter is the user object of the currently logged-in user. It is
    obtained by calling the get_user function, which is not shown in the code snippet.

    Returns:
      a dictionary with the following keys and values:
    - "status_code": status.HTTP_200_OK
    - "response_type": "SUCCESS"
    - "description": "User logged out"
    """
    db_user = samuraiUser.find_one({"samurai_id": current_user["samurai_id"]})
    if db_user is None:
        account_does_not_exist_error()
    samuraiUserToken.delete_one({"samurai_id": current_user["samurai_id"]})
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "User logged out",
    }


@router.delete(
    path="/auth/delete-user",
    status_code=status.HTTP_200_OK,
    summary="Delete User",
)
def delete_user(current_user=Depends(get_user)):
    db_user = samuraiUser.find_one({"samurai_id": current_user["samurai_id"]})
    if db_user is None:
        account_does_not_exist_error()
    samuraiDeletedUser.insert_one(db_user)
    samuraiUser.delete_one({"samurai_id": current_user["samurai_id"]})
    samuraiUserHistory.delete_many({"samurai_id": current_user["samurai_id"]})
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "User Deleted",
    }
