import json
import io
import os
import shutil
import requests
from uuid import uuid4
from bson.json_util import dumps
from fastapi import APIRouter, status, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from dataclasses import asdict
from models.schemas import ChatDetails, MessageDetails
from security.authorization import get_user
from models.payload import NewChatCreation, QuestionSchema, EditTitleName, Reaction
from exceptions.exceptions import (
    all_free_queries_used_error,
    chat_id_not_found_error,
    invalid_file_format_error,
    audio_not_clear_error,
    incorrect_style_error,
    video_generation_error,
    message_not_found_error,
)
from PIL import Image
from pydub import AudioSegment
from helper.utils import (
    image_gen_model,
    audio_translate,
    get_time,
    generate_talk,
)
from database.database import (
    samuraiUser,
    samuraiChatHistory,
    samuraiSystemPrompts,
)
from config.openai import openai
from config.settings import settings
from config.file_upload import upload_file
from config.google_cloud import speech_to_text, text_to_speech

router = APIRouter()


@router.post(
    path="/chat/create", status_code=status.HTTP_201_CREATED, summary="Create New chat"
)
def create_new_chat(payload: NewChatCreation, current_user=Depends(get_user)):
    if payload.catogeries_id:
        all_system_prompts_for_category = samuraiSystemPrompts.find_one(
            {"id": payload.catogeries_id}
        )
        for prompt in all_system_prompts_for_category["subCategories"]:
            if prompt["id"] == payload.catogeries_sub_id:
                system_prompt = prompt["prompt"]
        samuraiSystemPrompts.update_one(
            filter={
                "id": payload.catogeries_id,
                "subCategories.id": payload.catogeries_sub_id,
            },
            update={"$inc": {"subCategories.$.use_count": 1, "use_count": 1}},
        )
        chat_category_id, chat_sub_category_id = (
            payload.catogeries_id,
            payload.catogeries_sub_id,
        )
    else:
        system_prompt = chat_category_id = chat_sub_category_id = None
    chat_details = ChatDetails(
        samurai_id=current_user["samurai_id"],
        chat_prompt=system_prompt,
        chat_category_id=chat_category_id,
        chat_sub_category_id=chat_sub_category_id,
        chat_id=str(uuid4()),
    )
    samuraiChatHistory.insert_one(asdict(chat_details))
    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": "New Chat Created",
        "data": {"chat_id": chat_details.chat_id},
    }


@router.post(
    path="/chat/edit/title/",
    status_code=status.HTTP_202_ACCEPTED,
    summary="edit title name",
)
async def edit_title_name(payload: EditTitleName, current_user=Depends(get_user)):
    complete_chat = get_chat_by_id(current_user["samurai_id"], payload.chat_id)
    if not complete_chat:
        chat_id_not_found_error()
    samuraiChatHistory.update_one(
        filter={"samurai_id": current_user["samurai_id"], "chat_id": payload.chat_id},
        update={"$set": {"chat_title": payload.new_name}},
    )
    return {
        "status_code": status.HTTP_202_ACCEPTED,
        "response_type": "SUCCESS",
        "description": "Chat Name Changed",
    }


@router.post(
    path="/chat/reaction/",
    status_code=status.HTTP_202_ACCEPTED,
    summary="reaction for a message",
)
async def message_like_dislike(payload: Reaction, current_user=Depends(get_user)):
    def get_filter(message_id):
        return {
            "samurai_id": current_user["samurai_id"],
            "chat_id": payload.chat_id,
            "messages.message_id": message_id,
        }

    def update_reaction(message_id, is_liked=None):
        if is_liked is not None:
            update_operation = {
                "$set": {
                    "messages.$.is_liked": is_liked,
                    "messages.$.updated_at": get_time(),
                }
            }
        else:
            update_operation = {
                "$unset": {
                    "messages.$.is_liked": "",
                },
                "$set": {
                    "messages.$.updated_at": get_time(),
                },
            }
        samuraiChatHistory.update_one(
            filter=get_filter(message_id), update=update_operation
        )

    def generate_response(description):
        return {
            "status_code": status.HTTP_202_ACCEPTED,
            "response_type": "SUCCESS",
            "description": description,
        }

    message_id = payload.message_id
    message = samuraiChatHistory.find_one(
        filter=get_filter(message_id), projection={"messages.$": 1}
    )
    if not message:
        message_not_found_error()
    message_is_liked = message.get("messages", [{}])[0].get("is_liked", None)
    if message_is_liked is not None:
        if message_is_liked == payload.is_liked:
            update_reaction(message_id)
            if message_id % 2 == 0:
                update_reaction(message_id - 1)
            return generate_response("Message Reaction Removed")
    update_reaction(message_id, payload.is_liked)
    if message_id % 2 == 0:
        update_reaction((message_id - 1), payload.is_liked)
    return generate_response(f"Message is_liked {payload.is_liked}")


@router.delete(
    path="/chat/delete/{chat_id}",
    status_code=status.HTTP_200_OK,
    summary="Deleted chat",
)
def delete_chat(chat_id, current_user=Depends(get_user)):
    samuraiChatHistory.delete_one(
        filter={"samurai_id": current_user["samurai_id"], "chat_id": chat_id}
    )
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Chat Deleted",
        "data": {"chat_id": chat_id},
    }


@router.get(
    path="/chat/retrive/{chat_id}",
    status_code=status.HTTP_200_OK,
    summary="get all messages of a chat",
)
def chat_message(chat_id, current_user=Depends(get_user)):
    complete_chat = get_chat_by_id(current_user["samurai_id"], chat_id)
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Chat Data",
        "data": {
            "chat_id": complete_chat["chat_id"],
            "chat_title": complete_chat["chat_title"],
            "messages": complete_chat["messages"],
        },
    }


@router.get(
    path="/chat/all",
    status_code=status.HTTP_200_OK,
    summary="get all messages of a chat",
)
def get_all_chat_message(current_user=Depends(get_user)):
    all_chats = get_complete_chat_history(current_user["samurai_id"])
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Complete Chat Data",
        "data": json.loads(all_chats),
    }


@router.get(
    path="/chat/live-prompts",
    status_code=status.HTTP_200_OK,
    summary="get live prompts used by user",
)
def get_live_prompts():
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Live Prompts",
        "data": get_all_live_prompts(),
    }


@router.get(
    path="/chat/most-liked-prompts",
    status_code=status.HTTP_200_OK,
    summary="get most liked prompts˝",
)
def get_liked_prompts():
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Liked Prompts",
        "data": get_most_liked_prompts(),
    }


@router.get(
    path="/chat/system-prompts",
    status_code=status.HTTP_200_OK,
    summary="get all system prompts",
)
def get_all_chat_message():
    cursor = samuraiSystemPrompts.find({})
    doc: str = dumps(cursor, indent=4)
    return {
        "status_code": status.HTTP_200_OK,
        "response_type": "SUCCESS",
        "description": "Complete Chat Data",
        "data": json.loads(doc),
    }


@router.post(
    path="/chat/question/",
    status_code=status.HTTP_201_CREATED,
    summary="Response for question",
)
def gpt_answer_stream(payload: QuestionSchema, current_user=Depends(get_user)):
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    check_all_queries_used(db_user)
    new_messages = []
    chat_id: str = payload.chat_id
    question: str = payload.question
    complete_chat = get_chat_by_id(current_user["samurai_id"], chat_id)
    old_messages = complete_chat["messages"]
    chat_prompt = complete_chat["chat_prompt"]
    new_messages.append({"role": "user", "content": question})
    if old_messages != []:
        messages_for_openai, message_id = process_old_messages(
            old_messages=old_messages, chat_prompt=chat_prompt
        )
        messages_for_openai.append(new_messages[-1])
    else:
        if chat_prompt is not None:
            messages_for_openai, message_id = [
                {"role": "system", "content": chat_prompt},
                {"role": "user", "content": question},
            ], 0
        else:
            messages_for_openai, message_id = [{"role": "user", "content": question}], 0

    def msg_streamer(message, message_id, chat_id):
        streaming_answer = openai.ChatCompletion.create(
            model=settings["GPT_MODEL"], messages=message, stream=True
        )
        complete_answer = ""
        for chunk in streaming_answer:
            if "role" in chunk["choices"][0]["delta"]:
                if (
                    payload.regenerate_response is True
                    and message_id != 0
                    and payload.question == messages_for_openai[-3]["content"]
                ):
                    message_id -= 2
                yield f"{message_id+2}:message_id{chat_id}:chat_id"
            if "content" in chunk["choices"][0]["delta"]:
                word = chunk["choices"][0]["delta"]["content"]
                complete_answer += word
                yield word
            if chunk["choices"][0]["finish_reason"] == "stop":
                continue
        new_messages.append({"role": "assistant", "content": complete_answer})

        if message_id == 0:
            current_titles = get_all_current_titles(current_user["samurai_id"])
            chat_title = title_generator(complete_answer, current_titles)
        else:
            chat_title = None
        if payload.regenerate_response is True:
            if (
                len(messages_for_openai) not in [0, 1]
                and payload.question == messages_for_openai[-3]["content"]
            ):
                remove_message(
                    samurai_id=current_user["samurai_id"],
                    chat_id=chat_id,
                    message_id=message_id + 2,
                )
        insert_message(
            current_user["samurai_id"],
            chat_id,
            new_messages,
            message_id,
            "text",
            chat_title=chat_title,
        )

    return StreamingResponse(
        content=msg_streamer(messages_for_openai, message_id, chat_id),
        status_code=status.HTTP_200_OK,
        media_type="text/event-stream",
    )


def get_all_current_titles(samurai_id):
    all_chats = samuraiChatHistory.find({"samurai_id": samurai_id})
    current_titles = []
    for chat in all_chats:
        current_titles.append(chat["chat_title"])
    return current_titles


def title_generator(paragraph, current_titles=None):
    title_prompt = "generate a topic name for given paragraphs, topic or title should be less than 6 words, and should give a basic sum up of the paragraph."
    if current_titles is not None:
        title_prompt = f"{title_prompt} also make sure title or topic name is not one of these {current_titles}"
    messages = [
        {"role": "system", "content": title_prompt},
        {"role": "user", "content": paragraph},
    ]
    answer = openai.ChatCompletion.create(
        model=settings["GPT_MODEL"], messages=messages
    )
    title = answer["choices"][0]["message"]["content"]
    return title.replace('"', "")


def remove_message(samurai_id, chat_id, message_id):
    samuraiChatHistory.update_one(
        filter={"samurai_id": samurai_id, "chat_id": chat_id},
        update={
            "$pull": {"messages": {"message_id": {"$in": [message_id, message_id - 1]}}}
        },
    )


def insert_message(
    samurai_id,
    chat_id,
    messages,
    message_id,
    message_type,
    audio_text=None,
    chat_title=None,
):
    new_messages = []
    for i, message in enumerate(messages):
        if audio_text is not None:
            transcript = audio_text[i]
        else:
            transcript = None
        message_id += 1
        data = {
            "message_id": message_id,
            "message_role": message["role"],
            "message_type": message_type,
            "message_content": message["content"],
            "message_audio_text": transcript,
            "reaction": None,
            "created_at": get_time(),
            "updated_at": get_time(),
        }
        new_messages.append(data)
    update_query = {
        "$push": {"messages": {"$each": new_messages}},
        "$set": {"updated_at": get_time()},
    }
    if chat_title is not None:
        update_query["$set"]["chat_title"] = chat_title
    samuraiChatHistory.update_one(
        filter={"samurai_id": samurai_id, "chat_id": chat_id},
        update=update_query,
    )


@router.post(
    path="/chat/audio/",
    status_code=status.HTTP_201_CREATED,
    summary="Response for question as audio file",
)
def gpt_audio_answer(
    chat_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_user),
):
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    check_all_queries_used(db_user)

    if not file.filename.endswith(("mp3", "m4a")):
        invalid_file_format_error()
    with open(file.filename, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with io.open(file.filename, "rb") as audio_file:
        content = audio_file.read()
    link_question = upload_file("audio", file.filename)
    speech_to_text_response = speech_to_text(content)

    if speech_to_text_response.results == []:
        audio_not_clear_error()
    question = speech_to_text_response.results[0].alternatives[0].transcript
    language = speech_to_text_response.results[0].language_code
    old_messages: list = get_chat_by_id(current_user["samurai_id"], chat_id)["messages"]
    new_messages = [{"role": "user", "content": question}]
    if old_messages != []:
        messages_for_openai, message_id = process_old_messages(old_messages)
        messages_for_openai.append(new_messages[-1])
    else:
        messages_for_openai, message_id = [{"role": "user", "content": question}], 0

    complete_answer = openai.ChatCompletion.create(
        model=settings["GPT_MODEL"], messages=messages_for_openai
    )
    answer = complete_answer["choices"][0]["message"]["content"]
    text_to_speech_response = text_to_speech(answer, language)
    with open("converted_speech.mp3", "wb") as out:
        out.write(text_to_speech_response.audio_content)
    link_answer = upload_file("audio", "converted_speech.mp3")
    new_messages.append({"role": "assistant", "content": link_answer})
    audio_text = [question, answer]
    new_messages[0]["content"] = link_question
    if message_id == 0:
        current_titles = get_all_current_titles(current_user["samurai_id"])
        chat_title = title_generator(answer, current_titles)
    else:
        chat_title = None
    insert_message(
        current_user["samurai_id"],
        chat_id,
        new_messages,
        message_id,
        "audio",
        audio_text,
        chat_title=chat_title,
    )
    os.remove(file.filename)
    os.remove("converted_speech.mp3")
    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": "Audio Generated",
        "data": {
            "question": link_question,
            "question_text": question,
            "answer": link_answer,
            "answer_text": answer,
        },
    }


@router.post(
    path="/chat/audio/text/",
    status_code=status.HTTP_201_CREATED,
    summary="Response for question from audio in stream",
)
def gpt_audio_answer_stream(
    chat_id: str = Form(...),
    file: UploadFile = File(...),
    current_user=Depends(get_user),
):
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    check_all_queries_used(db_user)

    if not file.filename.endswith(("mp3", "m4a")):
        invalid_file_format_error()
    with open(file.filename, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    link_question = upload_file("audio", file.filename)
    old_messages: list = get_chat_by_id(current_user["samurai_id"], chat_id)["messages"]
    audio_file = open(file.filename, "rb+")
    question = audio_translate(audio_file)["text"]
    new_messages = [{"role": "user", "content": question}]
    os.remove(file.filename)
    if old_messages != []:
        messages_for_openai, message_id = process_old_messages(old_messages)
        messages_for_openai.append(new_messages[-1])
    else:
        messages_for_openai, message_id = new_messages, 0
    audio_text = [question]
    new_messages[0]["content"] = link_question

    insert_message(
        current_user["samurai_id"],
        chat_id,
        new_messages,
        message_id,
        "audio",
        audio_text,
    )
    messages_for_openai[-1]["content"] = question

    def msg_streamer(message):
        streaming_answer = openai.ChatCompletion.create(
            model=settings["GPT_MODEL"], messages=message, stream=True
        )
        complete_answer = ""
        for chunk in streaming_answer:
            if "role" in chunk["choices"][0]["delta"]:
                continue
            if "content" in chunk["choices"][0]["delta"]:
                word = chunk["choices"][0]["delta"]["content"]
                complete_answer += word
                yield word
        new_messages.append({"role": "assistant", "content": complete_answer})
        new_messages.pop(0)
        if message_id == 0:
            current_titles = get_all_current_titles(current_user["samurai_id"])
            chat_title = title_generator(complete_answer, current_titles)
        else:
            chat_title = None
        insert_message(
            current_user["samurai_id"],
            chat_id,
            new_messages,
            message_id + 1,
            "text",
            chat_title=chat_title,
        )

    return StreamingResponse(
        content=msg_streamer(messages_for_openai),
        status_code=status.HTTP_200_OK,
        media_type="text/event-stream",
    )


@router.post(
    path="/chat/image/",
    status_code=status.HTTP_201_CREATED,
    summary="Response for image",
)
async def image_generation(payload: QuestionSchema, current_user=Depends(get_user)):
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})
    check_all_queries_used(db_user)
    chat_id: str = payload.chat_id
    question = payload.question
    old_messages: list = get_chat_by_id(current_user["samurai_id"], chat_id)["messages"]
    new_messages = [{"role": "user", "content": question}]

    if old_messages != []:
        messages_for_openai, message_id = process_old_messages(old_messages)
        messages_for_openai.append(new_messages[-1])
    else:
        messages_for_openai, message_id = [{"role": "user", "content": question}], 0
    if message_id == 0:
        current_titles = get_all_current_titles(current_user["samurai_id"])
        chat_title = title_generator(question, current_titles)
    else:
        chat_title = None
    insert_message(
        current_user["samurai_id"],
        chat_id,
        new_messages,
        message_id,
        "text",
        chat_title=chat_title,
    )
    image = image_gen_model(question)
    generated_image = Image.open(io.BytesIO(image.content))
    generated_image.save("output.jpeg", "JPEG")
    link = upload_file("images", "output.jpeg")
    new_messages.append({"role": "assistant", "content": link})

    new_messages.pop(0)
    insert_message(
        current_user["samurai_id"],
        chat_id,
        new_messages,
        message_id,
        "image",
        chat_title=chat_title,
    )
    os.remove("output.jpeg")
    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": "Image Generated",
        "data": {"question": question, "link": link},
    }


@router.post(
    path="/chat/video/talk",
    status_code=status.HTTP_201_CREATED,
    summary="Creating a talk video",
)
async def talk_generation(
    file: UploadFile = File(...),
    script: str = Form(...),
    language: str = Form("english"),
    gender: str = Form("female"),
    style: str = Form(None),
    current_user=Depends(get_user),
):
    db_user = samuraiUser.find_one(filter={"samurai_id": current_user["samurai_id"]})

    # process chat_id later
    # chat_id = payload.chat_id
    # file = payload.file
    if (
        style is not None
        and language.lower() == "english"
        and style
        not in [
            "newscast",
            "angry",
            "cheerful",
            "sad",
            "excited",
            "friendly",
            "terrified",
            "shouting",
            "unfriendly",
            "whispering",
            "hopeful",
        ]
    ):
        incorrect_style_error()

    voice_models = {
        "english_male": "en-US-GuyNeural",
        "english_female": "en-US-JennyNeural",
        "hindi_male": "hi-IN-MadhurNeural",
        "hindi_female": "hi-IN-SwaraNeural",
    }
    model = voice_models[f"{language.lower()}_{gender.lower()}"]

    with open(file.filename, "wb+") as buffer:
        shutil.copyfileobj(file.file, buffer)
    image_link = upload_file("images", file.filename)
    response = generate_talk(image_link, script, model)
    if response["result"] == "error":
        video_generation_error(response["data"])

    response = requests.get(response["result"])
    with open("downloaded_video.mp4", "wb") as f:
        f.write(response.content)

    video_link = upload_file("video", "downloaded_video.mp4")

    os.remove(file.filename)
    os.remove("downloaded_video.mp4")

    return {
        "status_code": status.HTTP_201_CREATED,
        "response_type": "SUCCESS",
        "description": "Video Generated",
        "data": video_link,
    }


def check_all_queries_used(db_user):
    if db_user["subscription"]["active"] is False:
        if db_user["subscription"]["free_queries"] == 0:
            all_free_queries_used_error()
        samuraiUser.update_one(
            filter={"samurai_id": db_user["samurai_id"]},
            update={"$inc": {"subscription.free_queries": -1}},
        )


def get_complete_chat_history(samurai_id):
    cursor = samuraiChatHistory.find({"samurai_id": samurai_id}).sort(
        key_or_list="updated_at", direction=-1
    )
    doc: str = dumps(cursor, indent=4)
    return doc


def get_chat_by_id(samurai_id, chat_id):
    db_user = samuraiChatHistory.find_one(
        {"samurai_id": samurai_id, "chat_id": chat_id}
    )
    if db_user is None:
        chat_id_not_found_error()
    return db_user


def ogg_to_mp3(ogg_path, mp3_path):
    ogg_audio = AudioSegment.from_file(ogg_path)
    ogg_audio.export(mp3_path, format="mp3")


def get_all_live_prompts():
    pipeline = [
        {"$match": {"chat_category_id": {"$exists": True, "$ne": None}}},
        {"$unwind": "$messages"},
        {"$match": {"messages.message_role": "user"}},
        {"$sort": {"messages.updated_at": -1}},
        {
            "$group": {
                "_id": "$_id",
                "lastUserMessage": {"$first": "$messages.message_content"},
                "timestamp": {"$first": "$messages.updated_at"},
            }
        },
        {"$project": {"lastUserMessage": 1, "timestamp": 1}},
        {"$sort": {"timestamp": -1}},
    ]

    return [
        msg["lastUserMessage"] for msg in list(samuraiChatHistory.aggregate(pipeline))
    ]


def get_most_liked_prompts():
    pipeline = [
        {"$unwind": "$messages"},
        {"$match": {"messages.is_liked": True, "messages.message_role": "user"}},
        {"$sort": {"messages.updated_at": -1}},
        {"$project": {"message_content": "$messages.message_content", "_id": 0}},
        {"$limit": 50},
    ]
    return [msg["message_content"] for msg in samuraiChatHistory.aggregate(pipeline)]


def process_old_messages(old_messages, chat_prompt=None):
    messages_for_openai = []
    if chat_prompt is not None:
        messages_for_openai.append({"role": "system", "content": chat_prompt})

    # GPT is asked to consider last 10 messages only
    for message in old_messages:
        if message["message_type"] == "image":
            messages_for_openai.pop(-1)
            continue
        if message["message_type"] == "audio":
            openai_message = {
                "role": message["message_role"],
                "content": message["message_audio_text"],
            }
        else:
            openai_message = {
                "role": message["message_role"],
                "content": message["message_content"],
            }
        messages_for_openai.append(openai_message)
    message_id = old_messages[-1]["message_id"]
    return messages_for_openai, message_id
