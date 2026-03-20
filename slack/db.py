import boto3
import os

from botocore.exceptions import ClientError
from cryptography.fernet import Fernet
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("db")
session = boto3.Session(region_name="eu-central-1",aws_secret_access_key=os.getenv("aws_secret_access_key"),aws_access_key_id=os.getenv("aws_access_key_id"))
dynamodb = session.resource("dynamodb")
table = dynamodb.Table("flavorbot_api_keys")

FERNET = Fernet(os.getenv("enc_key").encode())
def encrypt_api_key(api_key: str) -> str:
    return FERNET.encrypt(api_key.encode()).decode()

def decrypt_api_key(encrypted_key: str) -> str:
    return FERNET.decrypt(encrypted_key.encode()).decode()
def init_db():
    return

def store_key(user_id: str,flavor_id:int, api_key: str):
    try:
        table.put_item(
            Item={
                #Ignore name just faulty table setup
                "discord_id":str(user_id),
                "api_key":encrypt_api_key(api_key),
                "flavor_id":flavor_id,
                "created_at":int(time.time())
            }
        )
    except ClientError as e:
        log.exception(e)

def get_api_key(user_id:str):
    try:
        resp = table.get_item(Key={"discord_id":str(user_id)})
        if resp.get("Item"):
            return [resp.get("Item").get("flavor_id"),decrypt_api_key(resp.get("Item").get("api_key"))]
    except ClientError as e:
        log.exception(e)
    return None

def del_api_key(user_id:str):
    try:
        resp = table.delete_item(
            Key={"discord_id":str(user_id)}
        )
    except ClientError as e:
        log.exception(e)