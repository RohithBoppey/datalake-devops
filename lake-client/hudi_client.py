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
            'hoodie.datasource.write.precombine.field': 'updated_at',
        }

        df.write.format("hudi").options(**hudi_options).mode("append").save(table_path)
        print("DF saved successfully")
    
    def get_history(self, spark, table_path):
        return (
            spark.read.format("hudi")
            .option("hoodie.datasource.query.type", "incremental")
            .option("hoodie.datasource.read.begin.instanttime", "0")
            .load(table_path)
        )
    
    def delete(self, spark, table_path, condition):
        tableName = table_path.split("/")[-1]

        # Read the rows that match the condition — these are the ones to delete
        df = self.read(spark, table_path).filter(condition)

        hudi_options = {
            'hoodie.table.name': tableName,
            'hoodie.datasource.write.operation': 'delete',
            'hoodie.datasource.write.recordkey.field': 'order_id',
            'hoodie.datasource.write.precombine.field': 'updated_at',
        }

        df.write.format("hudi").options(**hudi_options).mode("append").save(table_path)
        print(f"Deleted rows matching: {condition}")

if __name__ == "__main__":
    spark = get_spark("hudi")
    client = HudiClient()

    PATH = "s3a://lakehouse/hudi/orders"

    # --- Step 1: Initial write (creates the Hudi table) ---
    data = [
        {"order_id": "ORD-0001", "status": "created", "amount": 450, "updated_at": "2026-04-18T10:00:00+00:00"},
        {"order_id": "ORD-0002", "status": "created", "amount": 230, "updated_at": "2026-04-18T10:00:00+00:00"},
        {"order_id": "ORD-0003", "status": "created", "amount": 200, "updated_at": "2026-04-18T10:00:00+00:00"},
    ]

    df = spark.createDataFrame(data)
    client.write(df, PATH, ["order_id"])

    print("--- After initial write ---")
    client.read(spark, PATH).show(5)

    # --- Step 2: Upsert (update ORD-0001 + insert ORD-0004) ---
    upsert_data = [
        {"order_id": "ORD-0001", "status": "shipped", "amount": 450, "updated_at": "2026-04-18T11:00:00+00:00"},
        {"order_id": "ORD-0004", "status": "created", "amount": 999, "updated_at": "2026-04-18T10:00:00+00:00"},
    ]

    upsert_df = spark.createDataFrame(upsert_data)
    client.write(upsert_df, PATH, ["order_id"])

    print("--- After upsert ---")
    client.read(spark, PATH).show(5)

    # now delete the shipped orders 
    client.delete(spark, PATH, "status == 'shipped'")

    # now read again 
    print("--- After delete ---")
    client.read(spark, PATH).show(5)

    # show all the histories so far
    print("--- History (all changes since beginning) ---")
    client.get_history(spark, PATH).show()

    spark.stop() 
