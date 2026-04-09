# from hudi import 
from base import LakeTableClient
from config import get_spark

class HudiClient(LakeTableClient): 
    def __init__(self):
        pass 

    def read(self, spark, table_path):
        # read a dataframe
        df = spark.read.format("hudi").load(table_path)
        return df 
    
    def write(self, df, table_path, key_cols):
        tableName = table_path.split("/")[-1]

        hudi_options = {
            'hoodie.table.name': tableName,
            'hoodie.datasource.write.recordkey.field': key_cols[0],
            # 'hoodie.datasource.write.partitionpath.field': 'status',
            'hoodie.datasource.write.precombine.field': 'ts',
        }

        df.write.format("hudi").options(**hudi_options).mode("append").save(table_path)
        print("DF saved successfully")
    
    def get_history(self, spark, table_path):
        return super().get_history(spark, table_path)
    
    def delete(self, spark, table_path, condition):
        return super().delete(spark, table_path, condition)

if __name__ == "__main__":
    spark = get_spark("hudi")
    client = HudiClient()

    PATH = "s3a://lakehouse/hudi/orders"

    # --- Step 1: Initial write (creates the Hudi table) ---
    data = [
        {"order_id": "ORD-0001", "status": "created", "amount": 450, "ts": 1},
        {"order_id": "ORD-0002", "status": "created", "amount": 230, "ts": 1},
        {"order_id": "ORD-0003", "status": "created", "amount": 200, "ts": 1},
    ]

    df = spark.createDataFrame(data)
    client.write(df, PATH, ["order_id"])

    print("--- After initial write ---")
    client.read(spark, PATH).show(5)

    # --- Step 2: Upsert (update ORD-0001 + insert ORD-0004) ---
    upsert_data = [
        {"order_id": "ORD-0001", "status": "shipped", "amount": 450, "ts": 2},
        {"order_id": "ORD-0004", "status": "created", "amount": 999, "ts": 1},
    ]

    upsert_df = spark.createDataFrame(upsert_data)
    client.write(upsert_df, PATH, ["order_id"])

    print("--- After upsert ---")
    client.read(spark, PATH).show(5)
