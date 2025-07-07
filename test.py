from dotenv import load_dotenv
import os
load_dotenv()
api = os.getenv("API_KEY")

print(api)