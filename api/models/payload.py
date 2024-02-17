from pydantic import BaseModel, EmailStr, Field, conint
from fastapi import Form, UploadFile, File
from typing import Optional, Any
from helper.utils import *
from uuid import uuid4
from dataclasses import dataclass


class Samurai(BaseModel):
    question: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class SignUpSchema(BaseModel):
    samurai_id: str | None = None
    otp_secret: str | None = None
    name: str
    email: EmailStr
    password: str
    confirm_password: str
    stripe_id: str | None = None
    verified: bool = False
    subscription: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


class DeviceSignUp(BaseModel):
    device_id: str
    samurai_id: str | None = None
    otp_secret: str | None = None
    stripe_id: str | None = None
    profile_completed: bool | None = None
    name: str | None = None
    email: str | None = None
    account_type: str | None = None
    profile_picture: str | None = None
    verified: bool = False
    subscription: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


class UserOut(BaseModel):
    name: str
    email: EmailStr


class TokenSchema(BaseModel):
    access_token: str


class OTP(BaseModel):
    otp: str
    email: str


class ResendEmailOTP(BaseModel):
    email: str


class ForgetPassword(BaseModel):
    email: str
    otp: str
    new_password: str
    confirm_new_password: str


class PaymentIntent(BaseModel):
    email: str
    name: str | None = None
    plan: str
    amount: int
    currency: str
    telegramID: str | None = None


class PaymentIntentConfirmation(BaseModel):
    intent_id: str
    plan: str


class InAppPayment(BaseModel):
    subscribed: bool
    subscription_details: dict


class PlanDetails(BaseModel):
    plan_id: str
    name: str
    duration: str
    duration_in_days: int
    price: str


class SubscriptionDetails(BaseModel):
    type: str
    active: bool
    free_queries: int
    start_date: str | None = None
    end_date: str | None = None
    plan_details: PlanDetails | None = None


class UserSchema(BaseModel):
    email: EmailStr | None
    name: str | None
    verified: bool
    subscription: SubscriptionDetails | None = None
    profile_completed: bool | None = None
    account_type: str | None = None
    profile_picture: str | None = None
    verified: bool = False


class EditTitleName(BaseModel):
    chat_id: str
    new_name: str


class Reaction(BaseModel):
    chat_id: str
    message_id: conint(gt=0)
    is_liked: bool


@dataclass
class CompleteUser:
    email: EmailStr = Form(...)
    name: str = Form(...)
    account_type: str = Form(...)
    profile_picture: UploadFile = File(...)


class NewChatCreation(BaseModel):
    catogeries_id: int | None = None
    catogeries_sub_id: int | None = None


class QuestionSchema(BaseModel):
    chat_id: str
    question: str
    regenerate_response: bool | None = False


class VideoTalkSchema(BaseModel):
    # chat_id: str = Form(...)
    file: UploadFile = File(...)
    script: str = Form(...)
