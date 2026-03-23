Q. How to hit the HTTP API endpoint to interact with buckets, etc? 
A. CURL request is hard, so use the minio client from the browser (9001 port) or else the mc client from CLI (this would connect and give you flexibility) 
```
docker run --rm -it --network dataeng_devops_default \
  minio/mc alias set local http://minio:9000 minio minio123
```

```
docker run --rm -it \
  --network dataeng_devops_default \
  --entrypoint /bin/sh \
  minio/mc
```

```
mc alias set local http://minio:9000 minio minio123
```

```
mc mb local/cli-bucket 
# This creates a bucket (similar behaviour as creating one from UI)
```

or else can use the boto3 python client like how we use it for S3, etc. 
