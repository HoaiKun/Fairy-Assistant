from openai import OpenAI
from dotenv import load_dotenv
import re
import os
import json
load_dotenv();

FairyMain = OpenAI()
latest_response_id = None
tools = None

class StreamSentenceSplitter:
    def __init__(self):
        self.buffer = ""
        self.min_length = 15
        self.split_pattern = re.compile(r'([^.?!;\n]+[.?!;\n]+["\'”’\)\]]*)(\s+|$)', re.UNICODE)

    def feed(self, delta: str) ->list[str]:
        self.buffer += delta
        sentences = []

        while True:
            match = self.split_pattern.search(self.buffer)
            if not match:
                break
            candidate = match.group(1).strip()

            if len(candidate) < self.min_length:
                break

            if(candidate):
                sentences.append(candidate)
            self.buffer = self.buffer[match.end() :]

        return sentences

    def flush(self) -> list[str]:

        sentences = []
        
        while True:
            match = self.split_pattern.search(self.buffer)
            if not match:
                break
            candidate = match.group(1).strip()
            if(candidate):
                sentences.append(candidate)
            self.buffer = self.buffer[match.end() :]


        remaining = self.buffer.strip()
        
        if remaining:
            sentences.append(remaining)
        
        self.buffer = ""

        return sentences

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

    splitter = StreamSentenceSplitter()
    full_sentence_array = []
    

    for item in FairyResponse:

        if item.type == "response.created":
            latest_response_id = item.response.id

        elif item.type == "response.output_text.delta":
            delta = item.delta
            print(delta, end = "", flush=True)

            completed_sentence = splitter.feed(delta)
            for sentence in completed_sentence:
                full_sentence_array.append(sentence)

        elif item.type == "response.completed":
            latest_response_id = item.response.id

    leftover = splitter.flush()

    for sentence in leftover:
        full_sentence_array.append(sentence)

    print('\n ---')      
    print(full_sentence_array)


RunFairyMain(input = input())
RunFairyMain(input = input())
RunFairyMain(input = input())
