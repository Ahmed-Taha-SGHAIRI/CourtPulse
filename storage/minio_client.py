"""
storage/minio_client.py
────────────────────────────────────────────────────────────────────────────
MinIO utility helpers used by all ingestion scripts.

All functions read connection details from environment variables:
  MINIO_ENDPOINT      e.g. "minio:9000"
  MINIO_ROOT_USER     e.g. "minioadmin"
  MINIO_ROOT_PASSWORD e.g. "minioadmin"
────────────────────────────────────────────────────────────────────────────
"""

import io
import os

import pandas as pd
from minio import Minio
from minio.error import S3Error


def get_client() -> Minio:
    """Return a connected MinIO client (TLS disabled for internal networking)."""
    endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")
    access_key = os.environ.get("MINIO_ROOT_USER", "minioadmin")
    secret_key = os.environ.get("MINIO_ROOT_PASSWORD", "minioadmin")
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)


def ensure_bucket(client: Minio, bucket_name: str) -> None:
    """Create bucket if it does not already exist."""
    try:
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
    except S3Error as exc:
        if exc.code == "BucketAlreadyOwnedByYou":
            pass
        else:
            raise


def upload_parquet(client: Minio, df: pd.DataFrame, bucket: str, object_path: str) -> None:
    """Serialise DataFrame to Parquet and upload to MinIO."""
    ensure_bucket(client, bucket)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    buf.seek(0)
    size = buf.getbuffer().nbytes
    client.put_object(
        bucket_name=bucket,
        object_name=object_path,
        data=buf,
        length=size,
        content_type="application/octet-stream",
    )


def download_parquet(client: Minio, bucket: str, object_path: str) -> pd.DataFrame:
    """Download a Parquet object from MinIO and return as DataFrame."""
    response = client.get_object(bucket, object_path)
    buf = io.BytesIO(response.read())
    response.close()
    response.release_conn()
    return pd.read_parquet(buf)


def list_objects(client: Minio, bucket: str, prefix: str) -> list:
    """Return a list of object names under the given bucket/prefix."""
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    return [obj.object_name for obj in objects]
