import json
from fastapi import APIRouter, status, HTTPException, Depends
from models.payload import PaymentIntent, PaymentIntentConfirmation, InAppPayment
from security.authorization import get_user
from helper.utils import get_time
from utils.utils import create_ephemeral_key, create_intent, extend_time
from exceptions.exceptions import (
    account_does_not_exist_error,
    stripe_error,
    already_subscribed_user,
    already_unsubscribed_user,
    payment_error,
    payment_not_completed_error,
    payment_already_done_error,
    wrong_plan_error,
)
from bson.objectid import ObjectId
from bson.json_util import dumps
from database.database import (
    samuraiUser,
    samuraiSubscriptionPlans,
    samuraiSubscriptions,
)
from config.stripe import stripe


router = APIRouter()


@router.get(
    path="/payments/get-subscriptions",
    status_code=status.HTTP_200_OK,
    summary="All Subscriptions",
)
def subscriptions():
    """
    Returns subscriptions, currently static ,will be converted to dynamic
    """
    plans = samuraiSubscriptionPlans.find_one(
        {"_id": ObjectId("64b8e01a33c769ea301d5311")}
    )
    doc = dumps(plans, indent=4)
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Plan Details",
        "data": json.loads(doc),
    }


@router.post(
    path="/payments/intent/create",
    status_code=status.HTTP_201_CREATED,
    summary="create payment intent",
)
def intent(payload: PaymentIntent, current_user=Depends(get_user)):
    """
    creates payment intents
    """
    try:
        db_user = samuraiUser.find_one({"samurai_id": current_user["samurai_id"]})
        if db_user is None:
            account_does_not_exist_error()
        stripe_id = db_user["stripe_id"]
        intent_object = create_intent(payload, stripe_id)
        ephemeral_key = create_ephemeral_key(stripe_id)
        return {
            "status_code": status.HTTP_201_CREATED,
            "response_type": "SUCCESS",
            "description": "Intent Created",
            "data": {"PaymentIntent": intent_object, "ephemeralKey": ephemeral_key},
        }

    except stripe.error.StripeError as error:
        stripe_error(error)
    except Exception as all_error:
        payment_error(all_error)


@router.post(
    "/payments/confirm/",
    status_code=status.HTTP_200_OK,
    summary="Confirm Payment",
)
def confirm_payment(payload: PaymentIntentConfirmation, current_user=Depends(get_user)):
    complete_intent = retrieve_payment_intent(payload.intent_id)
    if complete_intent.status != "succeeded":
        payment_not_completed_error()
    db_user = samuraiUser.find_one({"stripe_id": complete_intent.customer})
    if db_user is None:
        account_does_not_exist_error()
    payment_intent_in_db = samuraiSubscriptions.find_one(
        {"intent_id": payload.intent_id}
    )
    if payment_intent_in_db is not None:
        payment_already_done_error()
    plan = samuraiSubscriptionPlans.find_one({"plan_id": payload.plan})
    if plan is None:
        wrong_plan_error()
    duration = plan["duration_in_days"]
    if db_user["subscription"]["active"] is True:
        start_date = db_user["subscription"]["end_date"]
    else:
        start_date = get_time()

    end_date = extend_time(start_date, duration)
    samuraiUser.update_one(
        filter={"samurai_id": current_user["samurai_id"]},
        update={
            "$set": {
                "subscription.type": "PAID",
                "subscription.active": True,
                "subscription.start_date": start_date,
                "subscription.end_date": end_date,
                "subscription.plan_details": plan,
                "updated_at": get_time(),
            }
        },
    )
    samuraiSubscriptions.insert_one(
        document={
            "samurai_id": current_user["samurai_id"],
            "intent_id": payload.intent_id,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": get_time(),
            "updated_at": get_time(),
        }
    )

    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": (
            "Subscription details Extended"
            if db_user["subscription"]["active"]
            else "New Subscription details saved"
        ),
    }


@router.post(
    "/payments/confirm/",
    status_code=status.HTTP_200_OK,
    summary="Confirm Payment",
)
def confirm_payment(payload: PaymentIntentConfirmation, current_user=Depends(get_user)):
    complete_intent = retrieve_payment_intent(payload.intent_id)
    if complete_intent.status != "succeeded":
        payment_not_completed_error()
    db_user = samuraiUser.find_one({"stripe_id": complete_intent.customer})
    if db_user is None:
        account_does_not_exist_error()
    payment_intent_in_db = samuraiSubscriptions.find_one(
        {"intent_id": payload.intent_id}
    )
    if payment_intent_in_db is not None:
        payment_already_done_error()
    plan = samuraiSubscriptionPlans.find_one({"plan_id": payload.plan})
    if plan is None:
        wrong_plan_error()
    duration = plan["duration_in_days"]
    if db_user["subscription"]["active"] is True:
        start_date = db_user["subscription"]["end_date"]
    else:
        start_date = get_time()

    end_date = extend_time(start_date, duration)
    samuraiUser.update_one(
        filter={"samurai_id": current_user["samurai_id"]},
        update={
            "$set": {
                "subscription.type": "PAID",
                "subscription.active": True,
                "subscription.start_date": start_date,
                "subscription.end_date": end_date,
                "subscription.plan_details": plan,
                "updated_at": get_time(),
            }
        },
    )
    samuraiSubscriptions.insert_one(
        document={
            "samurai_id": current_user["samurai_id"],
            "intent_id": payload.intent_id,
            "start_date": start_date,
            "end_date": end_date,
            "created_at": get_time(),
            "updated_at": get_time(),
        }
    )

    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": (
            "Subscription details Extended"
            if db_user["subscription"]["active"]
            else "New Subscription details saved"
        ),
    }


@router.post(
    "/payments/in-app/confirm/",
    status_code=status.HTTP_200_OK,
    summary="Active subscription",
)
def activate_subscription(payload: InAppPayment, current_user=Depends(get_user)):
    db_user = samuraiUser.find_one({"samurai_id": current_user["samurai_id"]})
    if db_user is None:
        account_does_not_exist_error()
    if payload.subscribed is True:
        if db_user["subscription"]["type"] == "paid":
            already_subscribed_user()
        type, active = "paid", True
    else:
        if db_user["subscription"]["type"] == "trial":
            already_unsubscribed_user()
        type, active = "trial", False
    samuraiUser.update_one(
        filter={"samurai_id": current_user["samurai_id"]},
        update={
            "$set": {
                "subscription.type": type,
                "subscription.active": active,
                "updated_at": get_time(),
            }
        },
    )
    # samuraiSubscriptions.insert_one()

    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
    }


def retrieve_payment_intent(intent_id):
    try:
        complete_intent = stripe.PaymentIntent.retrieve(intent_id)
    except stripe.error.StripeError as error:
        stripe_error(error)
    return complete_intent
