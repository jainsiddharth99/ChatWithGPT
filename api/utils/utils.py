from passlib.context import CryptContext
import os
from fastapi import HTTPException
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt
from config.stripe import stripe
from config.settings import settings
import pyotp
import smtplib
import pytz
from email.message import EmailMessage

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_time():
    current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
    time = current_time.strftime("%m/%d/%Y %H:%M:%S")
    converted_time = datetime.strptime(time, "%m/%d/%Y %H:%M:%S")
    return converted_time


def extend_time(time, days):
    converted_time = datetime.strptime(time, "%m/%d/%Y %H:%M:%S")
    converted_time += timedelta(days=days)
    return converted_time.strftime("%m/%d/%Y %H:%M:%S")


def get_secret_key_otp():
    return pyotp.random_base32()


def get_current_otp(secret):
    return pyotp.TOTP(secret, interval=180)


def send_email_otp(email, otp):
    msg = EmailMessage()
    msg["Subject"] = "OTP verification Samurai"
    msg["From"] = settings["EMAIL"]
    msg["To"] = email
    msg.set_content(f"Here is otp for verification - {otp}")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings["EMAIL"], settings["PASSWORD"])
        smtp.send_message(msg)


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_access_token(id: Union[str, Any], expires_delta: int = None) -> str:
    if expires_delta is not None:
        expires_delta = datetime.utcnow() + timedelta(days=expires_delta)
    else:
        expires_delta = datetime.utcnow() + timedelta(
            days=int(settings["ACCESS_TOKEN_EXPIRE_DAYS"])
        )

    to_encode = {
        "scope": "access_token",
        "exp": expires_delta,
        "samurai_id": id,
    }
    encoded_jwt = jwt.encode(to_encode, settings["SECRET_KEY"], settings["ALGORITHM"])
    return encoded_jwt


def decode_token(token):
    try:
        decoded_data: dict[str, Any] = jwt.decode(
            token, settings["SECRET_KEY"], settings["ALGORITHM"]
        )
        if decoded_data["scope"] != "access_token":
            raise HTTPException(
                status_code=401, detail="Scope for the token is invalid"
            )
        return decoded_data
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def create_customer(name, email):
    customer = stripe.Customer.create(name=name, email=email)
    return customer["id"]


def create_intent(payload, stripe_id):
    intent = stripe.PaymentIntent.create(
        amount=payload.amount,
        currency=payload.currency,
        payment_method_types=["card"],
        payment_method="pm_card_visa",
        customer=stripe_id,
    )
    return intent


def create_ephemeral_key(stripe_id):
    return stripe.EphemeralKey.create(customer=stripe_id, stripe_version="2022-11-15")
