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
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="HF repo id, e.g. ibm-granite/granite-7b-instruct")
    ap.add_argument("--bucket", required=True, help="S3 bucket name")
    ap.add_argument("--prefix", required=True, help="S3 prefix/folder to place the snapshot")
    ap.add_argument("--hf-token", dest="hf_token",
                default=os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN"))
    ap.add_argument("--endpoint", default=os.getenv("S3_ENDPOINT"), help="S3-compatible endpoint URL (omit for AWS)")
    ap.add_argument("--region", default=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    ap.add_argument("--access-key", default=os.getenv("AWS_ACCESS_KEY_ID"))
    ap.add_argument("--secret-key", default=os.getenv("AWS_SECRET_ACCESS_KEY"))
    ap.add_argument("--insecure", action="store_true", help="Skip TLS verify for self-signed MinIO")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.hf_token:
        login(args.hf_token)

    print(f"Downloading HF snapshot: {args.repo}")
    local_path = snapshot_download(repo_id=args.repo)
    print("Downloaded to:", local_path)

    session = boto3.session.Session(region_name=args.region)
    s3 = session.client(
        "s3",
        aws_access_key_id=args.access_key,
        aws_secret_access_key=args.secret_key,
        endpoint_url=args.endpoint or None,
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
    )

    print(f"Uploading to s3://{args.bucket}/{args.prefix.rstrip('/')}/ …")
    upload_dir_to_s3(local_path, args.bucket, args.prefix, s3, dry_run=args.dry_run)
    print("Done.")

if __name__ == "__main__":
    main()
