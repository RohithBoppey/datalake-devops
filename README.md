# Local Data Lake

A fully local, Dockerized mini data platform mimicking a production data lake architecture.
Focused on understanding the wiring — not scale. Replicable on a real on-prem server.

## Stack (Phase 1 — Foundation)

| Component | Tool | Purpose |
|-----------|------|---------|
| Storage | MinIO | S3-compatible local object store |
| Batch Processor | Apache Spark 3.5.0 | PySpark queries and batch processing |
| Table Format | Delta Lake 3.1.0 | ACID transactions, upserts, time travel |
| Infrastructure | Docker Compose | Container orchestration |

Future phases add Kafka (streaming), Flink (stream processing), Hudi/Iceberg (format swap), and Airflow (orchestration).

## Repo Structure

```
dataeng_devops/
├── lake-client/                 # Plug-and-play lake abstraction
│   ├── base.py                  # Abstract interface (write, read, delete, get_history)
│   ├── delta_client.py          # Delta Lake implementation
│   └── config/
│       ├── spark_session.py     # Spark session factory with S3A config
│       └── setup_minio.py       # Creates the MinIO bucket via boto3
├── producer/
│   └── seed_orders.py           # Generates 20 orders, demos full CRUD + history
├── spark-jobs/                  # Batch Spark jobs (Phase 2+)
├── documentation/               # Planning docs and phase-wise notes
├── Dockerfile                   # Spark image with Delta + boto3
├── spark-setup.yaml             # Docker Compose: Spark Master + Worker
├── run-minio.yaml               # Docker Compose: MinIO
├── export.sh                    # Env vars for running locally
└── .env.example                 # Credential template
```

## Quick Start

### 1. Start the containers

```bash
docker compose -f run-minio.yaml up -d
docker compose -f spark-setup.yaml up -d
```

### 2. Create the MinIO bucket

```bash
python3 lake-client/config/setup_minio.py
```

### 3. Set environment variables

```bash
source export.sh
```

### 4. Run the seed script

```bash
python3 producer/seed_orders.py
```

This writes 20 orders to `s3a://lakehouse/orders`, upserts new records, deletes cancelled orders, and prints the transaction history.

## Key Design: Plug-and-Play Interface

All data operations go through the `LakeTableClient` abstract interface. To swap table formats, change one line:

```python
# Current
client = DeltaClient()

# Future (Phase 4)
client = HudiClient()
client = IcebergClient()
```

The interface provides four operations:
- **write** — upsert (merge on key columns, insert new / update existing)
- **read** — snapshot read of the current table state
- **delete** — remove rows matching a SQL condition
- **get_history** — full transaction log for auditing and time travel

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAENG_S3_URL` | `http://localhost:9000` | MinIO endpoint |
| `DATAENG_S3_ACCESS_KEY` | `minio` | MinIO access key |
| `DATAENG_S3_SECRET_KEY` | `minio123` | MinIO secret key |

When running inside Docker, set `DATAENG_S3_URL` to `http://minio:9000` (Docker DNS).

## Ports

| Service | Port | URL |
|---------|------|-----|
| MinIO API | 9000 | http://localhost:9000 |
| MinIO Console | 9001 | http://localhost:9001 |
| Spark Master UI | 8080 | http://localhost:8080 |
| Spark Worker UI | 8081 | http://localhost:8081 |

## Roadmap

- **Phase 1** — MinIO + Spark + Delta Lake (current)
- **Phase 2** — Kafka event streaming
- **Phase 3** — Flink stream processing
- **Phase 4** — Hudi & Iceberg clients (plug-and-play swap)
- **Phase 5** — Airflow orchestration
