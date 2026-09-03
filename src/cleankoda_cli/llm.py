import os
from dotenv import load_dotenv
from mistralai.client import Mistral


load_dotenv()  # Loads variables from .env into os.environ

api_key = os.getenv("API_KEY")
model_name = "mistral-medium-latest"

client = Mistral(api_key=api_key)
