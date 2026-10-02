import os

from dotenv import load_dotenv
from imagekitio import ImageKit

load_dotenv()

# The current ImageKit Python SDK authenticates server-side uploads with the private key.
# Public key / URL endpoint can still be kept in .env for future client-side delivery features.
imagekit = ImageKit(private_key=os.getenv("IMAGEKIT_PRIVATE_KEY"))
