
# Consumes order events from Kafka in micro-batches and writes them to Delta Lake
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lake-client"))

from pyspark.sql import Window
import pyspark.sql.functions as F

from clients.kafka import KafkaBatchConsumer
from clients.kafka.config import get_kafka_config
from config import get_spark
from delta_client import DeltaClient

# Config
kafka_config = get_kafka_config()

KAFKA_TOPIC_NAME = os.environ.get("KAFKA_TOPIC", "orders")
CONSUMER_GROUP_ID = "order-lake-writer"
BATCH_SIZE = 10
BATCH_TIMEOUT = 10

S3_TABLE_PATH = "s3a://lakehouse/orders"
KEY_COLS = ["order_id"]


def make_process_batch(spark, lake_client):
    """Return a callback that converts a batch to a DataFrame and upserts to Delta."""
    batch_count = 0

    def process_batch(messages: list[dict]) -> None:
        nonlocal batch_count
        batch_count += 1

        df = spark.createDataFrame(messages)

        # Deduplicate: keep only the latest event per order_id within this batch
        window = Window.partitionBy("order_id").orderBy(F.col("updated_at").desc())
        df = df.withColumn("_rank", F.row_number().over(window)) \
               .filter(F.col("_rank") == 1) \
               .drop("_rank")

        lake_client.write(df, S3_TABLE_PATH, KEY_COLS)
        print(f"  Batch #{batch_count}: wrote {df.count()} records to {S3_TABLE_PATH}")

    return process_batch


if __name__ == "__main__":
    spark = get_spark()
    lake_client = DeltaClient()

    consumer = KafkaBatchConsumer(
        topic=KAFKA_TOPIC_NAME,
        group_id=CONSUMER_GROUP_ID,
        bootstrap_servers=kafka_config["bootstrap_servers"],
        batch_size=BATCH_SIZE,
        batch_timeout_s=BATCH_TIMEOUT,
    )

    print(f"Consuming '{KAFKA_TOPIC_NAME}' → Delta at '{S3_TABLE_PATH}'")
    consumer.consume(process_fn=make_process_batch(spark, lake_client))
