# Context Prompt — Data Lake Local Setup (Continue From Here)

## Who I Am
I am a developer with the following background:
- Familiar with Python, Golang, and a little Scala
- Have worked with Apache Spark, HDFS, Hue/Ambari in the past (seen Parquet files in HDFS, written Airflow DAGs)
- Learning data lake concepts from scratch in a hands-on way
- Running on M4 Pro Mac

## How I Want You to Help Me
- **Do not write code unless I explicitly ask**
- Guide me to figure things out myself first
- When I write code, review it and point out issues conceptually before giving fixes
- Explain concepts simply with real-world analogies before going technical
- Track progress phase by phase and sub-task by sub-task
- Ask clarifying questions before proceeding to the next step
- When I'm stuck, ask leading questions rather than giving direct answers

---

## The Project

A fully local, Dockerized mini data platform mimicking a production data lake architecture.
**Goal:** Understand the wiring, not the scale. Replicable on a real on-prem server later.

### Full Stack
| Component | Tool |
|---|---|
| Storage | MinIO (S3-compatible, free, open source) |
| Message broker | Apache Kafka |
| Stream processor | Apache Flink (Java jobs) |
| Batch processor | Apache Spark (PySpark) |
| Table formats | Delta Lake / Hudi / Iceberg (plug and play) |
| Orchestration | Apache Airflow (added in Phase 5) |

### Repo Structure
```
data-lake-local/
├── docker/
├── producer/
├── flink-jobs/         # Java, Maven
├── spark-jobs/         # PySpark scripts
├── lake-client/        # Plug-and-play abstraction
│   ├── __init__.py
│   ├── base.py         # Abstract interface (DONE)
│   ├── delta_client.py # IN PROGRESS
│   ├── hudi_client.py  # Phase 4
│   └── iceberg_client.py # Phase 4
├── config/
│   └── spark_session.py  # DONE
└── docker-compose.yml
```

### Design Pattern — Plug and Play
The table format is a swappable implementation behind a common interface.
Swapping Delta → Hudi → Iceberg is a **one line change**:
```python
from lake_client.delta_client import DeltaLakeClient as Client  # only this changes
client = Client()
# everything below is identical
client.write(df, TABLE_PATH, key_cols=["order_id"])
```

### Data Domain
E-commerce orders stream:
- Events: order created → updated → cancelled
- Exercises upserts and deletes naturally
- Schema: `order_id`, `status`, `amount`, `updated_at`

---

## Phase Tracker

### Phase 1 — Foundation: MinIO + Spark + Delta Lake
**Goal:** Simplest end-to-end. Write data → Delta table on MinIO → read back with Spark.

```
✅ 1.1 — Docker Compose: MinIO + Spark
         - MinIO running with 2 ports (9000 S3 API, 9001 Console UI)
         - Spark master + worker running (apache/spark:3.5.0 base)
         - Custom Dockerfile built on top adding delta-spark==3.1.0
         - Volumes mounted: lake-client/ and spark-jobs/ into /opt/spark/work-dir/
         - All containers on same Docker network (dataeng_devops_default) ✅ verified
         - Spark container can reach MinIO at http://minio:9000 ✅ verified

✅ 1.2 — MinIO bucket
         - Bucket creation approach decided (boto3 / mc CLI / Console UI)
         - NOTE: bucket "lakehouse" may still need to be created — verify this

✅ 1.3 — Plug-and-play interface
         - base.py written with 4 abstract methods:
           * write(df, table_path, key_cols) — upsert
           * read(spark, table_path) — read latest snapshot
           * delete(spark, table_path, condition) — delete by SQL condition
           * get_history(spark, table_path) — transaction history / time travel

✅ 1.4 — spark_session.py written
         - get_spark(format="delta") function
         - Loads 3 JARs: delta-spark, hadoop-aws, aws-java-sdk-bundle
         - MinIO endpoint: http://minio:9000 (internal Docker network)
         - Credentials: minio / minio123
         - S3A path style access enabled
         - Stub comments for Hudi/Iceberg left for Phase 4

🔄 1.5 — delta_client.py — IN PROGRESS
         See current state and issues below.

⬜ 1.6 — seed_orders.py — not started
```

### Phase 2 — Add Kafka ⬜
### Phase 3 — Add Flink (Java) ⬜
### Phase 4 — Plug and Play: Hudi + Iceberg ⬜
### Phase 5 — Add Airflow ⬜

---

## Key Concepts Already Explained (Do Not Re-Explain Unless Asked)
- What a data lake is vs a database
- HDFS / Parquet / Spark / Hue relationship
- What MinIO is and how it relates to S3
- S3 as a protocol standard (not just an AWS product)
- boto3 working with MinIO despite AWS-specific features
- Why Docker volumes are mounted (containers are isolated)
- Named volumes vs bind mounts
- What delta-spark (Python) vs Delta JAR (Java) each do
- The steering wheel vs engine analogy for Python package vs JAR
- What spark_session.py does and why it's separate
- PySpark shell vs spark-submit
- Where scripts run (inside container, not on Mac)
- The two-case logic for write() (insert vs upsert)
- How DeltaTable.merge() works conceptually

---

## Important Technical Decisions Made
- **Storage:** MinIO from day one (not plain filesystem) — free, open source, S3-compatible
- **Scripts run inside the Spark container** (not on Mac) — closer to real server setup
- **MinIO endpoint inside container:** `http://minio:9000` (Docker internal DNS)
- **Flink jobs:** Java only (not PyFlink)
- **Glue layer:** Python
- **Single repo:** Yes, monorepo
- **Airflow:** Added last (Phase 5)
- **Delta Lake first** among the three formats — smoothest PySpark integration
- **Custom Dockerfile** for Spark image (not install-at-startup) — production habit

## Versions Locked
- Spark: 3.5.0
- delta-spark: 3.1.0 (must match Spark 3.5.x)
- hadoop-aws: 3.3.4
- aws-java-sdk-bundle: 1.12.262
- Flink: 1.18.x (Phase 3)
