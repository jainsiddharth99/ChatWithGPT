from fastapi import status, HTTPException


def account_exists_error():
    """
    Raises account exists error
    """
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ACCOUNT EXISTS")


def account_does_not_exist_error():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="ACCOUNT DOES NOT EXIST"
    )


def stripe_error(error):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
    ) from error


def already_subscribed_user():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="User is already subscribed."
    )


def already_unsubscribed_user():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="User is already unsubscribed."
    )


def payment_error(error):
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)
    ) from error


def payment_not_completed_error():
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="payment not completed"
    )


def payment_already_done_error():
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="payment not completed"
    )


def wrong_plan_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Wrong plan name, valid names [week,month,quarter]",
    )


def password_does_not_match_error():
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="PASSWORD DOES NOT MATCH CONFIRM PASSWORD",
    )


def password_length_error():
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="PASSWORD LENGTH MUST BE MORE THEN 8 AND LESS THEN 16 CHARACTERS",
    )


def incorrect_password_error():
    raise HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="INCORRECT PASSWORD"
    )


def wrong_otp_error():
    raise HTTPException(status_code=status.HTTP_406_NOT_ACCEPTABLE, detail="WRONG OTP")


def account_not_verified_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="ACCOUNT NOT VERIFIED, OTP SENT"
    )


def all_free_queries_used_error():
    raise HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail="Your credits have been depleted. Earn more to unlock new messages.",
    )


def profile_already_completed_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Profile Already Completed."
    )


def reacted_again_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Message already has a same reaction",
    )


def chat_id_not_found_error():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Chat id not found, or was deleted",
    )


def message_not_found_error():
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="message id not found, or was deleted",
    )


def invalid_file_format_error():
    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="Invalid file format. Only audio files are allowed.",
    )


def audio_not_clear_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Audio is not clear, record it again",
    )


def incorrect_business_error():
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Wrong business type provided,the ones acceptable is ->business,team,student",
    )


def incorrect_style_error():
    raise HTTPException(
        status_code=status.HTTP_406_NOT_ACCEPTABLE,
        detail="Valid style type not sent. Valid types-newscast,angry,sad,cheerful,friendly,terrified,shouting,unfriendly,whispering and hopeful",
    )


def video_generation_error(error):
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
