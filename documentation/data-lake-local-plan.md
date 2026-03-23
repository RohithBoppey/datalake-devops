# Local Data Lake Implementation Plan

> **Goal:** A fully local, Dockerized mini data platform mimicking a production data lake architecture.
> Focused on understanding the wiring — not scale. Replicable on a real on-prem server.

---

## Stack Overview

| Component | Tool | Purpose |
|---|---|---|
| Storage | MinIO | S3-compatible local object store |
| Message broker | Apache Kafka | Event streaming |
| Stream processor | Apache Flink (Java) | Real-time stream processing |
| Batch processor | Apache Spark (PySpark) | Batch reads and queries |
| Table formats | Delta Lake / Hudi / Iceberg | ACID transactions on the lake |
| Orchestration | Apache Airflow | Batch job scheduling (added later) |
| UI tools | Kafka UI, Flink UI, MinIO Console, Spark UI | Observability |

**All tools are free and open source.**

---

## Repo Structure

```
data-lake-local/
├── docker/           # docker-compose files, one per phase
├── producer/         # Python order event generator and consumer
├── flink-jobs/       # Java Flink jobs (Maven project)
├── spark-jobs/       # PySpark query and batch scripts
├── lake-client/      # Plug-and-play table format abstraction (Python)
├── airflow/          # Airflow DAGs (added in Phase 5)
├── config/           # Shared configs (Kafka topics, Spark session, MinIO setup)
└── README.md
```

---

## Phase 1 — Foundation: MinIO + Spark + Delta Lake

**Goal:** Get the simplest possible end-to-end working. Write data to a Delta table on MinIO, read it back with Spark. No Kafka, no Flink. Validates the storage and compute layer, and establishes the plug-and-play interface.

```
Python seed script → Delta table → MinIO bucket → PySpark reads it back
```

### Steps

**1.1 — Docker Compose: MinIO + Spark**
- Spin up a MinIO container with two ports: one for the S3 API, one for the MinIO Console UI
- Spin up a Bitnami Spark master and a Spark worker container
- Mount the `spark-jobs/` and `lake-client/` directories into the Spark container
- Use a named Docker volume for MinIO data persistence

**1.2 — Create MinIO bucket**
- Write a small Python script in `config/setup_minio.py` using `boto3`
- Connect to MinIO using the local endpoint URL and root credentials
- Create a bucket called `lakehouse` — this is where all lake data will live

**1.3 — Define the plug-and-play interface**
- Create `lake-client/base.py` with an abstract base class `LakeTableClient`
- Define four abstract methods that every table format client must implement:
  - `write(df, table_path, key_cols)` — insert or upsert records
  - `read(spark, table_path)` — read the full table as a DataFrame
  - `delete(spark, table_path, condition)` — delete rows matching a SQL condition
  - `get_history(spark, table_path)` — return the transaction/commit history

**1.4 — Implement Delta Lake client**
- Create `lake-client/delta_client.py` implementing `LakeTableClient`
- `write` uses Delta's merge (upsert) when the table already exists, otherwise does an initial overwrite
- `delete` uses `DeltaTable.delete()`
- `get_history` uses `DeltaTable.history()`

**1.5 — Shared Spark session factory**
- Create `config/spark_session.py` with a `get_spark(format)` function
- Accept a format argument (`"delta"`, `"hudi"`, or `"iceberg"`) to load the correct JARs via `spark.jars.packages`
- Configure all S3A settings pointing to MinIO here — endpoint, access key, secret key, path-style access
- This is the **only file that changes** when you move from MinIO to real S3 (remove endpoint, swap credentials)

**1.6 — Seed script**
- Create `producer/seed_orders.py`
- Generate 20 synthetic orders as a Spark DataFrame (order_id, status, amount, updated_at)
- Instantiate `DeltaLakeClient` — this is the one line that changes to swap formats later
- Write to `s3a://lakehouse/orders` using `client.write()`
- Read back and print to confirm

### Validation Checklist
- [ ] MinIO Console at `localhost:9001` shows `lakehouse` bucket containing Parquet files and a `_delta_log/` directory
- [ ] `client.read()` returns all 20 orders correctly
- [ ] `client.delete()` removes a record and `read()` confirms it is gone
- [ ] `client.get_history()` shows the transaction log entries

### S3 Difference
When moving to real S3: remove the MinIO service from docker-compose, remove `fs.s3a.endpoint` from the Spark config, and replace the access key and secret with IAM credentials or an instance role. Nothing else changes.

---

## Phase 2 — Add Kafka: Real Event Streaming

**Goal:** Replace the static seed script with a live Kafka producer generating a continuous stream of order events. A Python consumer reads from Kafka and writes micro-batches to Delta Lake. Flink is not involved yet — this phase proves the Kafka-to-lake path.

```
Python producer → Kafka topic "orders" → Python consumer → Delta table on MinIO
```

### Steps

**2.1 — Add Kafka to Docker Compose**
- Add Zookeeper and Kafka (Confluent Platform images) to the compose file
- Expose Kafka on `localhost:9092` for the producer running outside Docker
- Add Kafka UI (provectuslabs/kafka-ui) on `localhost:8090` — free, open source
- Configure Kafka with a single broker and set replication factor to 1 for local use

**2.2 — Order event producer**
- Create `producer/order_producer.py`
- Generate events in a continuous loop with a short sleep between each
- Cycle through 200 order IDs so the same IDs repeat — this naturally exercises upserts
- Each event has: `order_id`, `status` (randomly chosen from created/paid/shipped/delivered/cancelled), `amount`, `updated_at`
- Serialize to JSON and send to the `orders` Kafka topic

**2.3 — Kafka to Delta consumer**
- Create `producer/order_consumer.py`
- Connect to Kafka with a consumer group ID so offsets are tracked
- Accumulate events into a local list; flush to Delta Lake every 10 events as a micro-batch
- Use the same `DeltaLakeClient` and `client.write()` as Phase 1 — no interface changes needed

**2.4 — Topic setup**
- Add a small utility script in `config/` to create the `orders` Kafka topic with appropriate partition count before running the producer

### Validation Checklist
- [ ] Kafka UI at `localhost:8090` shows messages flowing on the `orders` topic
- [ ] Consumer writes batches to MinIO, files are visible in the MinIO console
- [ ] Running producer and consumer simultaneously shows the Delta table updating in real time
- [ ] Because 200 order IDs cycle, the table stays at ~200 rows — confirming upserts work, not just appends

---

## Phase 3 — Add Flink: Real Stream Processing

**Goal:** Replace the Python consumer with a proper Java Flink job. Flink reads from Kafka, applies stream transformations (splitting events by status), and writes to Delta Lake via the Flink-Delta connector. This is the heart of the real-time pipeline.

```
Kafka → Flink job (Java) → Delta table: "orders" (active)
                         ↘ Delta table: "orders_cancelled"
```

### Steps

**3.1 — Maven project setup**
- Create `flink-jobs/` as a Maven Java project
- Add dependencies: `flink-streaming-java`, `flink-connector-kafka`, `delta-flink`, `hadoop-aws`
- Use Flink 1.18.x and the matching connector versions

**3.2 — Order event POJO**
- Create `model/OrderEvent.java` with fields matching the Kafka event schema
- Add a custom JSON deserializer so Flink can parse incoming Kafka messages

**3.3 — Delta sink factory**
- Create `sink/DeltaSinkFactory.java` as a utility that builds a configured `DeltaSink` for a given S3A path
- Configure Hadoop S3A settings (endpoint, credentials, path-style access) inside the factory so the main job stays clean

**3.4 — Main Flink job**
- Create `OrderStreamJob.java`
- Enable checkpointing (required for the Delta sink to guarantee exactly-once writes)
- Build a Kafka source pointed at the `orders` topic with a watermark strategy
- Split the stream into two using `filter`: active orders (non-cancelled) and cancelled orders
- Attach a Delta sink to each stream writing to separate MinIO paths

**3.5 — Add Flink to Docker Compose**
- Add Flink JobManager and TaskManager containers (Flink 1.18 Java 11 image)
- Expose the Flink UI on `localhost:8081`
- Pass S3/MinIO config via `FLINK_PROPERTIES` environment variable
- Configure TaskManager with enough task slots for both sinks

**3.6 — Build and submit the job**
- Build the Maven project into a fat JAR (`mvn package`)
- Submit via the Flink UI or `flink run` CLI
- Document the submit command in the README

### Validation Checklist
- [ ] Flink UI at `localhost:8081` shows the job running with two active sinks
- [ ] Both `lakehouse/orders` and `lakehouse/orders_cancelled` appear in MinIO
- [ ] `client.read(spark, "s3a://lakehouse/orders_cancelled").count()` grows over time as cancelled events arrive
- [ ] Flink checkpoints appear in MinIO under `s3a://lakehouse/_checkpoints/`
- [ ] Stopping and restarting the Flink job resumes from the last checkpoint without data loss

---

## Phase 4 — Plug-and-Play: Swap Delta → Hudi → Iceberg

**Goal:** Implement the Hudi and Iceberg clients behind the same `LakeTableClient` interface. Prove that swapping the entire table format is a one-line change. Run the full pipeline with each format and observe the differences in file layout.

### Steps

**4.1 — Implement Hudi client**
- Create `lake-client/hudi_client.py` implementing `LakeTableClient`
- `write` uses PySpark's Hudi datasource format with upsert operation, setting `hoodie.datasource.write.recordkey.field` to the key columns and `precombine.field` to `updated_at`
- `delete` reads existing records, flags them with `_hoodie_is_deleted`, and writes back with the delete operation
- `get_history` reads from the `.hoodie/` metadata directory
- Note: add `.option("hoodie.embed.timeline.server", "false")` to avoid issues with non-HDFS storage

**4.2 — Implement Iceberg client**
- Create `lake-client/iceberg_client.py` implementing `LakeTableClient`
- `write` uses `df.writeTo().using("iceberg").createOrReplace()`
- `delete` uses a Spark SQL `DELETE FROM` statement
- `get_history` uses `spark.sql("SELECT * FROM table.history")`

**4.3 — Update Spark session factory**
- Extend `config/spark_session.py` to load the correct JARs and Spark extensions for Hudi and Iceberg
- Iceberg requires adding the `SparkSessionExtensions` and configuring the Iceberg catalog
- Hudi requires the Hudi bundle JAR and Kryo serializer config

**4.4 — Test the one-line swap**
- In `producer/seed_orders.py` and `producer/order_consumer.py`, the client instantiation is a single import and instantiation line
- Run the full pipeline (seed → read → delete → history) with all three clients in turn
- Document the observed differences in MinIO file structure:
  - Delta Lake: `_delta_log/` directory with JSON transaction log
  - Hudi: `.hoodie/` directory with timeline files
  - Iceberg: `metadata/` directory with manifest files

**4.5 — Wire Flink to Hudi and Iceberg (stretch)**
- Flink has connectors for all three formats
- Swap the `DeltaSink` in the Java job for the Hudi or Iceberg Flink sink
- This requires a separate Maven dependency swap — document this in the README as the Java equivalent of the one-line Python swap

### Validation Checklist
- [ ] All four operations (write, read, delete, get_history) work correctly with HudiClient
- [ ] All four operations work correctly with IcebergClient
- [ ] Switching between all three clients requires changing exactly one line in the pipeline scripts
- [ ] MinIO shows distinct folder/file structures for each format
- [ ] Transaction history is visible and meaningful for all three formats

---

## Phase 5 — Add Airflow: Batch Orchestration

**Goal:** Wire in Apache Airflow to schedule a daily batch Spark job. The job reads from the live orders table, computes an aggregated report (orders grouped by status), and writes the report as a new table back to MinIO. This phase connects your existing DAG experience to the lake setup.

```
Airflow DAG (daily schedule) → triggers PySpark job → reads orders table → writes report table to MinIO
```

### Steps

**5.1 — Add Airflow to Docker Compose**
- Add an Airflow container (apache/airflow:2.9.0) to the compose file
- Expose the Airflow UI on `localhost:8082`
- Mount `airflow/dags/` and `spark-jobs/` into the container
- Use LocalExecutor with SQLite for simplicity (no separate Postgres needed for local dev)
- Run `airflow db init` and create an admin user on first start

**5.2 — Write the PySpark report job**
- Create `spark-jobs/orders_report.py`
- Read from `s3a://lakehouse/orders` using the configured `LakeTableClient`
- Group by `status`, count records, compute average amount per status
- Write the result to `s3a://lakehouse/orders_report` as a new Delta/Hudi/Iceberg table
- The format used should be configurable via an environment variable so the DAG can pass it in

**5.3 — Write the Airflow DAG**
- Create `airflow/dags/orders_report_dag.py`
- Schedule it `@daily`
- Use a `BashOperator` to invoke `spark-submit` on the report job
- Add a second task that prints the row count of the report table as a sanity check
- Wire the tasks with `>>` so the count check runs only after the report job succeeds

**5.4 — Connect Spark submit to the Spark cluster**
- Configure the `spark-submit` command in the DAG to point at the Spark master (`spark://spark:7077`)
- Pass the MinIO credentials as `--conf` flags so the report job can write to S3A

### Validation Checklist
- [ ] Airflow UI at `localhost:8082` shows the DAG and its task history
- [ ] Manually triggering the DAG runs the Spark job successfully
- [ ] `lakehouse/orders_report` appears in MinIO after the DAG run
- [ ] The report table contains one row per status with correct counts and averages
- [ ] Scheduling the DAG and waiting for the next trigger confirms automatic execution

---

## Limitations

### M4 Pro / ARM Architecture
- Some Flink and Hadoop JARs include platform-specific native libraries built for x86
- Use `--platform linux/amd64` in Docker image declarations for Flink and Spark containers if you encounter crashes or missing native library errors
- This works but runs through Rosetta 2 emulation, so it is slower than native ARM

### Flink + Delta Connector Maturity
- The `delta-flink` connector is less mature than the Spark-Delta integration
- Exactly-once guarantees require careful checkpoint configuration
- Acceptable for local learning; on production you would tune checkpoint intervals and storage carefully

### Hudi on MinIO
- Hudi's embedded timeline server occasionally has issues with non-HDFS storage backends
- If you hit `HoodieTableMetaClient` errors, disable the embedded server with `.option("hoodie.embed.timeline.server", "false")`

### No Real HDFS
- MinIO is S3-compatible, not HDFS-compatible at the protocol level
- The `s3a://` connector bridges this for most operations, but HDFS has slightly different consistency semantics
- For learning purposes this is irrelevant; for a true HDFS replication you would swap MinIO for an actual HDFS cluster — or keep MinIO, which many real on-prem setups do

### Flink State Backend
- Locally, Flink uses in-memory or RocksDB state
- On a real server, point state storage at HDFS or S3 via `state.backend: filesystem` and `state.checkpoints.dir: s3a://...`
- The change is two config lines

### Resource Usage
- Running all services simultaneously (MinIO + Kafka + Flink + Spark + Airflow) consumes approximately 8–10 GB of RAM
- M4 Pro handles this comfortably but close other memory-heavy applications if Spark jobs run out of memory

### Airflow + Spark Integration
- In this local setup, Airflow submits Spark jobs via BashOperator which is simple but not production-grade
- On a real cluster you would use the `SparkSubmitOperator` with a configured Spark connection, or submit jobs to a dedicated cluster via the Livy REST API

---

## Moving to a Real Server (On-Prem)

When you are ready to replicate this on a real server, the changes are minimal:

| What changes | How |
|---|---|
| MinIO → real S3 | Remove MinIO service, remove `fs.s3a.endpoint` config, add IAM credentials |
| Single-node Kafka → cluster | Increase broker count and replication factor in Kafka config |
| Single Spark worker → cluster | Add more worker nodes pointing at the same Spark master |
| Single Flink TaskManager → cluster | Add TaskManager containers or deploy to a standalone Flink cluster |
| Docker Compose → production | Use Docker Swarm, Nomad, or Kubernetes to orchestrate the same containers |
| SQLite Airflow → production | Swap SQLite for Postgres and LocalExecutor for CeleryExecutor |

The application code — the producer, Flink job, Spark jobs, and lake client — requires **zero changes**.
