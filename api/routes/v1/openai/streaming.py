from fastapi import APIRouter, status, UploadFile, File, HTTPException
from helper.utils import *
import shutil
from database.database import data
from models.payload import Samurai
from samurai.api.get_logger import logger
from fastapi.responses import StreamingResponse
import os


router = APIRouter()


@router.post("/stream/answer-audio")
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
            return StreamingResponse(
                streamer(prompt),
                status_code=status.HTTP_200_OK,
                media_type="text/event-stream",
            )

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/stream/question")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns streming response
    """
    try:
        prompt = obj.question

        return StreamingResponse(
            streamer(prompt),
            status_code=status.HTTP_200_OK,
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/stream/no-buffer/question")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns streming response with buffer json objects
    """
    try:
        prompt = obj.question
        message = [{"role": "user", "content": prompt}]
        return StreamingResponse(
            streamer_buffer(message),
            status_code=status.HTTP_200_OK,
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }


@router.post("/stream/no-buffer/prompt-generator")
async def gpt(obj: Samurai):
    """
    Gets prompt and returns streming response with buffer json objects
    """
    try:
        prompt = obj.question
        message = [
            {"role": "system", "content": "act as a prompt generator."},
            {
                "role": "assistant",
                "content": "Of course! I can help generate prompts for various creative endeavors or thought-provoking exercises. Let me know what specific type of prompts you're interested in, and I'll be glad to assist you.",
            },
            {"role": "user", "content": prompt},
        ]
        return StreamingResponse(
            streamer_buffer(message),
            status_code=status.HTTP_200_OK,
            media_type="text/event-stream",
        )

    except Exception as e:
        logger.error(str(e))
        return {
            "status_code": status.HTTP_404_NOT_FOUND,
            "response_type": "ERROR",
            "description": str(e),
        }
