import base64
import boto3
from google.cloud import speech
from google.oauth2 import service_account
import json
from config.index import CURRENT_ENV, S3_BUCKET_NAME
import os




# Initialize AWS S3 client
s3 = boto3.client("s3",
    region_name = "ap-south-2" if CURRENT_ENV == "dev" else "ap-south-1"
)


# Get the current working directory and build the path to the credentials file
file_path = os.path.join(os.path.dirname(__file__), 'google-services.json')

# Load the Google Cloud credentials from the JSON file
with open(file_path, 'r') as json_file:
    google_credentials_str = json_file.read()



# Initialize Google Cloud Speech client
credentials = service_account.Credentials.from_service_account_info(json.loads(google_credentials_str))
client = speech.SpeechClient(credentials=credentials)

def transcribe_audio_from_s3(file_name):
    print(f"Transcribing audio from S3: {file_name}")

    # Get the audio file from S3
    s3_bucket_name =  S3_BUCKET_NAME # Assuming S3_BUCKET_NAME is set as an environment variable
    try:
        s3_object = s3.get_object(Bucket=s3_bucket_name, Key=file_name)
        print("Audio file successfully downloaded from S3.")
    except Exception as e:
        print(f"Error downloading audio file from S3: {str(e)}")
        return None

    # The audio file's content is in s3_object['Body'] as a stream
    audio_bytes = s3_object["Body"].read()

    # Convert audio to base64
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

    # Set up audio and config for speech recognition
    audio = speech.RecognitionAudio(content=audio_base64)

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.MP3,  # Adjust the encoding if necessary
        sample_rate_hertz=16000,  # Adjust based on the audio sample rate
        language_code="en-US",  # Adjust the language code if necessary
    )

    # Call Google Cloud's Speech-to-Text API to transcribe the audio
    try:
        response = client.recognize(config=config, audio=audio)
        print(f"Response: {response}")
        
        # Extract the transcript from the response
        transcript = response.results[0].alternatives[0].transcript if response.results else None

        print(f"Transcript: {transcript}")
        return transcript
    except Exception as e:
        print(f"Error during transcription: {str(e)}")
        return None
