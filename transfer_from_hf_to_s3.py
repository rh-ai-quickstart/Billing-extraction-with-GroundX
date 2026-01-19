#! /usr/sbin/python3.11
# transfer_from_hf_to_s3.py
#pip install huggingface_hub boto3 botocore tqdm

import os, sys, argparse, pathlib
from tqdm import tqdm
from huggingface_hub import login, snapshot_download
import boto3
from botocore.client import Config

def upload_dir_to_s3(local_dir, bucket, prefix, s3, dry_run=False):
    local_dir = pathlib.Path(local_dir)
    for p in local_dir.rglob("*"):
        if p.is_file():
            rel = p.relative_to(local_dir).as_posix()
            key = f"{prefix.rstrip('/')}/{rel}"
            if dry_run:
                print("DRYRUN put:", bucket, key)
                continue
            s3.upload_file(str(p), bucket, key)

def main():
    hf_token = "REPLACE_WITH_YOUR_HF_TOKEN"
    repo = "RedHatAI/gemma-3-12b-it-quantized.w4a16"

    s3_endpoint = os.environ.get('AWS_S3_ENDPOINT')
    s3_region = os.environ.get('AWS_DEFAULT_REGION')
    s3_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    s3_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    s3_bucket = os.environ.get('AWS_S3_BUCKET')
    s3_path = "REPLACE_WITH_PATH_TO_MODEL"
    insecure = "true"
    dry_run = "false"
    
    if hf_token:
        login(hf_token)

    print(f"Downloading HF snapshot: {repo}")
    local_path = snapshot_download(repo)
    print("Downloaded to:", local_path)

    session = boto3.session.Session(region_name=s3_region)
    s3 = session.client(
        "s3",
        aws_access_key_id=s3_access_key,
        aws_secret_access_key=s3_secret_access_key,
        endpoint_url=s3_endpoint or None,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
    )

    print(f"Uploading to s3://{s3_bucket}/{s3_path.rstrip('/')}/ …")
    upload_dir_to_s3(local_path, s3_bucket, s3_path, s3, dry_run=dry_run)
    print("Done.")

if __name__ == "__main__":
    main()
