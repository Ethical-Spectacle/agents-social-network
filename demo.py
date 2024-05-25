import os
import sys
import requests
from dotenv import load_dotenv

class CLIChat:
    def __init__(self, api_url):
        self.api_url = api_url

    def chat(self):
        print("Start chatting with the model (type 'exit' to stop):")
        while True:
            question = input("You: ")
            if question.lower() == 'exit':
                print("Exiting the chat.")
                break

            response = self._send_request(question)
            print(f"Model: {response}")

    def _send_request(self, question):
        try:
            response = requests.post(
                self.api_url, json={"question": question}, stream=True
            )
            response.raise_for_status()

            full_response = ""
            for chunk in response.iter_content(chunk_size=1):
                if chunk:
                    full_response += chunk.decode('utf-8')
            
            return full_response.strip()
        except requests.RequestException as e:
            return f"An error occurred: {e}"

load_dotenv()
api_url = "http://127.0.0.1:5000/chat"
cli_chat = CLIChat(api_url)
cli_chat.chat()