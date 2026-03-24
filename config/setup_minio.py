# This file is create the S3 bucket required using the boto3 client

import boto3
import os

# config for connecting to boto3 via the S3 language
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minio")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_KEY_ID", "minio123")
LOCAL_MINIO_URL = f"http://localhost:9000"

s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    endpoint_url=LOCAL_MINIO_URL
)

print("S3 Client successfully connected")

def ListBuckets(s3_client: boto3.client): 
    resp = s3_client.list_buckets()
    bucket_names = [buck['Name'] for buck in resp.get('Buckets', [])]
    return bucket_names

# now create a bucket dynamically! 
try: 
    buckets = ListBuckets(s3_client)
    print('Existing buckets: ', buckets)

    # creating a new bucket
    response = s3_client.create_bucket(
        Bucket='lakehouse',
    )
    print(response)

except Exception as e: 
    if isinstance(e, s3_client.exceptions.BucketAlreadyOwnedByYou):
        print('Error while creating a bucket: ', e)
    else: 
        print("Error: ", e)