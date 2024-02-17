from urllib import response
from fastapi import APIRouter, status, UploadFile, File, HTTPException
from helper.utils import *
import shutil
from database.database import data
from models.payload import Samurai
from samurai.api.get_logger import logger
from fastapi.responses import StreamingResponse, FileResponse
from bson.objectid import ObjectId
import os
import io


router = APIRouter()


@router.post("/question")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns its answer
    """
    try:
        prompt = obj.question
        answer = data.find_one(
            {
                "_id": ObjectId("645a15383bea252b4af1f9c9"),
                f"{prompt}": {"$exists": True},
            }
        )
        if answer is None:
            messages = [{"role": "user", "content": prompt}]
            val = chat_completion(messages)
            answer = val["choices"][0]["message"]["content"]
            data.update_one(
                {"_id": ObjectId("645a15383bea252b4af1f9c9")},
                {"$set": {prompt: answer}},
            )
        else:
            answer = answer[prompt]
        response = {
            "status_code": status.HTTP_200_OK,
            "response_type": "SUCCESS",
            "description": "SamurAI answer",
            "body": obj,
            "response": answer,
        }
        logger.info(response)
        return response

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/image")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns image
    """
    try:
        prompt = obj.question
        try:
            os.remove("output.jpeg")
        except:
            pass
        image = image_gen_model(prompt)
        generated_image = Image.open(BytesIO(image.content))
        generated_image.save("output.jpeg", "JPEG")
        response = FileResponse("output.jpeg")
        return response

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/image-old")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns image
    """
    try:
        prompt = obj.question
        answer = data.find_one(
            {
                "_id": ObjectId("64646bf3496eec988f799c78"),
                f"{prompt}": {"$exists": True},
            }
        )
        if answer is None:
            image = image_generation(prompt)
            answer = image["data"][0]["url"]
            data.update_one(
                {"_id": ObjectId("64646bf3496eec988f799c78")},
                {"$set": {prompt: answer}},
            )
        else:
            answer = answer[prompt]
        # image = image_gen_model(prompt)
        # generated_image = Image.open(BytesIO(image.content))
        # generated_image.save("output.jpeg", "JPEG")
        # os.remove("output.jpeg")
        response = {
            "status_code": status.HTTP_200_OK,
            "response_type": "SUCCESS",
            "description": "SamurAI answer",
            "body": obj,
            "response": answer,
        }
        logger.info(response)
        # return FileResponse("output.jpeg")

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/prompt-generator")
async def gpt(obj: Samurai):
    """
    returns an awesome prompt
    """
    try:
        prompt = obj.question
        answer = data.find_one(
            {
                "_id": ObjectId("6464aa287269ddd982d95fab"),
                f"{prompt}": {"$exists": True},
            }
        )
        if answer is None:
            messages = [
                {"role": "system", "content": "act as a prompt generator."},
                {
                    "role": "assistant",
                    "content": "Of course! I can help generate prompts for various creative endeavors or thought-provoking exercises. Let me know what specific type of prompts you're interested in, and I'll be glad to assist you.",
                },
                {"role": "user", "content": prompt},
            ]
            val = chat_completion(messages)
            answer = val["choices"][0]["message"]["content"]
            data.update_one(
                {"_id": ObjectId("6464aa287269ddd982d95fab")},
                {"$set": {prompt: answer}},
            )
        else:
            answer = answer[prompt]
        response = {
            "status_code": status.HTTP_200_OK,
            "response_type": "SUCCESS",
            "description": "SamurAI answer",
            "body": obj,
            "response": answer,
        }
        logger.info(response)
        return response

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/audio")
async def gpt(file: UploadFile = File(...)):
    """
    returns translated text for audio
    """
    try:
        if not file.filename.endswith(
            ("mp3", "mp4", "m4a", "mpeg", "mpga", "wav", "webm")
        ):
            return HTTPException(
                status_code=400,
                detail="Invalid file format. Only audio files are allowed.",
            )
        else:
            with open(file.filename, "wb+") as buffer:
                shutil.copyfileobj(file.file, buffer)
            audio_file = open(file.filename, "rb+")
            transcript = audio_translate(audio_file)
            os.remove(file.filename)

            response = {
                "status_code": status.HTTP_200_OK,
                "response_type": "SUCCESS",
                "description": "SamurAI answer",
                "response": transcript,
            }
            logger.info(response)
            return response
    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/answer-audio")
async def gpt(file: UploadFile = File(...)):
    """
    returns translated text for audio
    """
    try:
        if not file.filename.endswith(
            ("mp3", "mp4", "m4a", "mpeg", "mpga", "wav", "webm")
        ):
            return HTTPException(
                status_code=400,
                detail="Invalid file format. Only audio files are allowed.",
            )
        else:
            with open(file.filename, "wb+") as buffer:
                shutil.copyfileobj(file.file, buffer)
            audio_file = open(file.filename, "rb+")
            prompt = audio_translate(audio_file)["text"]
            os.remove(file.filename)
            answer = data.find_one(
                {
                    "_id": ObjectId("645a15383bea252b4af1f9c9"),
                    f"{prompt}": {"$exists": True},
                }
            )
            if answer is None:
                messages = [{"role": "user", "content": prompt}]
                val = chat_completion(messages)
                answer = val["choices"][0]["message"]["content"]
                data.update_one(
                    {"_id": ObjectId("645a15383bea252b4af1f9c9")},
                    {"$set": {prompt: answer}},
                )
            else:
                answer = answer[prompt]
            response = {
                "status_code": status.HTTP_200_OK,
                "response_type": "SUCCESS",
                "description": "SamurAI answer",
                "transcript": prompt,
                "response": answer,
            }
            logger.info(response)
            return response

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }
