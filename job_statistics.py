import sys
sys.path.insert(0, "lake-client")

from config import get_spark
from delta_client import DeltaClient

ORDERS_PATH = "s3a://lakehouse/orders"
CANCELLED_PATH = "s3a://lakehouse/orders_cancelled"


def print_table_stats(client, spark, table_name, table_path):
    print("=" * 60)
    print(f"Table: {table_name}")
    print(f"Path:  {table_path}")
    print("=" * 60)

    # Read and show sample rows
    delta_table = client.read(spark, table_path)
    df = delta_table.toDF()

    print(f"\nSample rows (5):")
    df.show(5, False)

    print(f"Total records: {df.count()}")

    # History
    history_df = client.get_history(spark, table_path)
    print(f"\nTotal history entries (checkpoint commits): {history_df.count()}")
    print("\nHistory:")
    history_df.show(truncate=False)


if __name__ == "__main__":
    spark = get_spark("delta", app_name="JobStatistics")
    client = DeltaClient()

    print_table_stats(client, spark, "Active Orders", ORDERS_PATH)
    print("\n")
    print_table_stats(client, spark, "Cancelled Orders", CANCELLED_PATH)

    spark.stop()
