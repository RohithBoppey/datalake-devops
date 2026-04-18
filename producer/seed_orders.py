# This script:
# - simulates 20 orders
# - creates a spark DF
# - create a client
# use all the functions of the lake client

import sys
import os

# add lake-client to the path so we can import from it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lake-client"))

from config import get_spark
from delta_client import DeltaClient
from hudi_client import HudiClient
from base import LakeTableClient
from order_generator import generate_orders

FORMAT = "hudi"
S3_TABLE_PATH = f"s3a://lakehouse/{FORMAT}/orders"
KEY_COLS = ["order_id"]

def get_client() -> LakeTableClient:
    """
    Return the lake client to use.
    Swap formats by changing FORMAT at the top of this file.
    """
    if FORMAT == "delta":
        return DeltaClient()
    if FORMAT == "hudi":
        return HudiClient()
    raise ValueError(f"Unknown format: {FORMAT}")

if __name__ == "__main__":
    spark = get_spark(FORMAT)
    client: LakeTableClient = get_client()

    # 1. Create a DataFrame with 20 orders
    orders = generate_orders()
    df = spark.createDataFrame(orders)
    print("Created DataFrame:")
    df.show(20, truncate=False)

    # 2. Write to the lake
    print(f"\n--- Writing to {S3_TABLE_PATH} ---")
    client.write(df, S3_TABLE_PATH, KEY_COLS)

    # 3. Read back
    print(f"\n--- Reading from {S3_TABLE_PATH} ---")
    read_df = client.read(spark, S3_TABLE_PATH)
    read_df.show(20, truncate=False)

    # 4. Upsert: update existing + insert new orders
    print("\n--- Upserting records ---")
    upsert_data = [
        {"order_id": "ORD-0001", "status": "delivered", "amount": 450},   # update
        {"order_id": "ORD-0005", "status": "cancelled", "amount": 285},   # update
        {"order_id": "ORD-0021", "status": "created", "amount": 777},     # new
    ]
    upsert_df = spark.createDataFrame(upsert_data)
    client.write(upsert_df, S3_TABLE_PATH, KEY_COLS)

    read_df = client.read(spark, S3_TABLE_PATH)
    read_df.show(25, truncate=False)

    # 5. Delete some rows
    print("\n--- Deleting cancelled orders ---")
    client.delete(spark, S3_TABLE_PATH, "status = 'cancelled'")

    read_df = client.read(spark, S3_TABLE_PATH)
    read_df.show(25, truncate=False)

    # 6. Check history
    print(f"\n--- Transaction history for {S3_TABLE_PATH} ---")
    history_df = client.get_history(spark, S3_TABLE_PATH)
    history_df.show(10, truncate=False)

    print("\nAll lake client operations completed successfully.")
