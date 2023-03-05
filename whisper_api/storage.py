from minio import Minio
from datetime import timedelta
from minio.error import S3Error
import os
import uuid


bucket_name = os.environ.get("MINIO_BUCKET_NAME")

# Create a minio client
client = Minio(
    endpoint=os.environ.get("MINIO_ENDPOINT"),
    access_key=os.environ.get("MINIO_ACCESS_KEY"),
    secret_key=os.environ.get("MINIO_SECRET_KEY"),
)

# make sure bucket exists
if not client.bucket_exists(bucket_name):
    try:
        client.make_bucket(bucket_name)
    except S3Error as exc:
        print("error occurred creating bucket.", exc)


def store_file(uuid, file_path, file_name):
    """
    Stores a file in the minio bucket
    """

    try:
        client.fput_object(bucket_name, f"{uuid}/{file_name}", file_path)
    except S3Error as exc:
        print("error occurred storing file.", exc)


def get_file_name(uuid) -> str:
    """
    Returns the name of the file
    """

    try:
        objects = client.list_objects(bucket_name, prefix=f"{uuid}/", recursive=True)
        # return first object_name
        for obj in objects:
            return obj.object_name
    except S3Error as exc:
        print("error occurred getting file name.", exc)


def get_file(uuid) -> str:
    """
    Returns a presigned url to download the file
    """

    try:
        return client.presigned_get_object(
            bucket_name,
            get_file_name(uuid),
            expires=timedelta(hours=2),
        )
    except S3Error as exc:
        print("error occurred getting file.", exc)
