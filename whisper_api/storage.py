from minio import Minio
from minio import timedelta
from minio.error import S3Error
import os


bucket_name = os.environ.get("MINIO_BUCKET_NAME")

try:
    # Create a minio client
    client = Minio(
        os.environ.get("MINIO_ENDPOINT"),
        access_key=os.environ.get("MINIO_ACCESS_KEY"),
        secret_key=os.environ.get("MINIO_SECRET_KEY"),
    )

    # make sure bucket exists
    if not client.bucket_exists(bucket_name):
        try:
            client.make_bucket(bucket_name)
        except S3Error as exc:
            print("error occurred creating bucket.", exc)

except S3Error as exc:
    print("error occurred connecting to minio.", exc)


def store_file(uuid, file_path, file_name):
    """
    Stores a file in the minio bucket
    """

    try:
        client.fput_object(bucket_name, f"{uuid}/{file_name}", file_path)
    except S3Error as exc:
        print("error occurred storing file.", exc)


def get_file(uuid) -> str:
    """
    Returns a presigned url to download the file
    """

    try:
        return client.presigned_get_object(
            bucket_name,
            client.list_objects(bucket_name, prefix=f"{uuid}/", recursive=True)
            .objects[0]
            .object_name,
            expires=timedelta(hours=2),
        )
    except S3Error as exc:
        print("error occurred getting file.", exc)
