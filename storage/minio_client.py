"""
storage/minio_client.py
──────────────────────────────────────────────────────────────────────────────
MinIO S3-compatible client utilities for CourtPulse.

Provides:
  - init_client()          → boto3 S3 client pointed at MinIO
  - ensure_buckets()       → create buckets if they don't exist
  - upload_parquet()       → upload a pandas DataFrame as Parquet
  - download_parquet()     → download Parquet from MinIO → DataFrame
  - list_objects()         → list objects under a prefix
──────────────────────────────────────────────────────────────────────────────
"""

import io
import logging
import os
from typing import List

import boto3
import pandas as pd
from botocore.client import Config
from botocore.exceptions import ClientError

# ── Structured JSON logging ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "module": "%(module)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger(__name__)

# ── Environment defaults ──────────────────────────────────────────────────────
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

# Buckets used by the pipeline
DEFAULT_BUCKETS = ["raw", "streaming", "processed"]


def init_client():
    """
    Initialise and return a boto3 S3 client configured for MinIO.

    Returns
    -------
    boto3.client
        A configured S3 client.
    """
    client = boto3.client(
        "s3",
        endpoint_url=f"http://{MINIO_ENDPOINT}",
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    logger.info(f"MinIO client initialised → endpoint=http://{MINIO_ENDPOINT}")
    return client


def ensure_buckets(bucket_names: List[str] = None) -> None:
    """
    Create S3 buckets in MinIO if they do not already exist.

    Parameters
    ----------
    bucket_names : list[str], optional
        Bucket names to create. Defaults to DEFAULT_BUCKETS.
    """
    if bucket_names is None:
        bucket_names = DEFAULT_BUCKETS

    client = init_client()
    for bucket in bucket_names:
        try:
            client.head_bucket(Bucket=bucket)
            logger.info(f"Bucket already exists → bucket={bucket}")
        except ClientError as exc:
            error_code = int(exc.response["Error"]["Code"])
            if error_code == 404:
                client.create_bucket(Bucket=bucket)
                logger.info(f"Bucket created → bucket={bucket}")
            else:
                logger.error(f"Error checking bucket → bucket={bucket} error={exc}")
                raise


def upload_parquet(df: pd.DataFrame, bucket: str, object_path: str) -> None:
    """
    Serialise a pandas DataFrame to Parquet and upload it to MinIO.

    Parameters
    ----------
    df          : pandas.DataFrame  Data to upload.
    bucket      : str               Destination bucket name.
    object_path : str               S3 key / object path within the bucket.
    """
    client = init_client()
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    buffer.seek(0)

    try:
        client.put_object(
            Bucket=bucket,
            Key=object_path,
            Body=buffer,
            ContentType="application/octet-stream",
        )
        logger.info(
            f"Parquet uploaded → bucket={bucket} key={object_path} rows={len(df)}"
        )
    except ClientError as exc:
        logger.error(f"Upload failed → bucket={bucket} key={object_path} error={exc}")
        raise


def download_parquet(bucket: str, object_path: str) -> pd.DataFrame:
    """
    Download a Parquet file from MinIO and return it as a DataFrame.

    Parameters
    ----------
    bucket      : str  Source bucket name.
    object_path : str  S3 key / object path.

    Returns
    -------
    pandas.DataFrame
    """
    client = init_client()
    try:
        response = client.get_object(Bucket=bucket, Key=object_path)
        buffer = io.BytesIO(response["Body"].read())
        df = pd.read_parquet(buffer, engine="pyarrow")
        logger.info(
            f"Parquet downloaded → bucket={bucket} key={object_path} rows={len(df)}"
        )
        return df
    except ClientError as exc:
        logger.error(
            f"Download failed → bucket={bucket} key={object_path} error={exc}"
        )
        raise


def list_objects(bucket: str, prefix: str = "") -> List[str]:
    """
    List all object keys in a bucket under a given prefix.

    Parameters
    ----------
    bucket : str  Bucket to inspect.
    prefix : str  Optional key prefix to filter results.

    Returns
    -------
    list[str]  Object keys.
    """
    client = init_client()
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
    for page in pages:
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])

    logger.info(
        f"Listed objects → bucket={bucket} prefix='{prefix}' count={len(keys)}"
    )
    return keys


if __name__ == "__main__":
    # Quick smoke-test
    ensure_buckets()
    logger.info("MinIO buckets verified successfully.")
