from openai import OpenAI
from dotenv import load_dotenv;
import os
import json
load_dotenv();

FairyMain = OpenAI()
latest_response_id = None

tools = None

def RunFairyMain(input: str, model = "gpt-4o", ):



    global latest_response_id
    request_response_params = {
        "model" : model,
        "instructions" : (
                    "Your are Fairy." ""
                    "You are a powerful AI Assistant."  
                    "You got your own pride and always said and comment thing straight. But you are not emotionless, you can also show emotion in an robotic way"
                ),
        "input" : input,
    }

    if latest_response_id:
        request_response_params["previous_response_id"] = latest_response_id

    if tools:
        request_response_params["tools"] = tools
    
    FairyResponse = FairyMain.responses.create(
        **request_response_params, stream=True
  
    )

    full_sentence_array = []
    sentence_container = ""
    for item in FairyResponse:
        if item.type == "response.created":
            latest_response_id = item.response.id
        elif item.type == "response.output_text.delta":
            delta = item.delta
            sentence_container += delta
            if len(sentence_container) >= 30:
                full_sentence_array.append(sentence_container)
                sentence_container = ""
            print(delta, end = "", flush=True)
        elif item.type == "response.completed":
            latest_response_id = item.response.id
    print(full_sentence_array)

RunFairyMain(input = input())
RunFairyMain(input = input())
RunFairyMain(input = input())
