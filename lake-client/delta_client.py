# Implement the functions from the common interface

from base import LakeTableClient
from config import get_spark
from delta import DeltaTable

class DeltaClient(LakeTableClient): 
    # overwriting the functions needed 
    def __init__(self):
        pass

    def write(self, df, table_path, key_cols):
        # check if the delta table is present 
        spark = df.sparkSession
        if DeltaTable.isDeltaTable(spark, table_path):
            print("Table already present")
            return 
        
        # Creating a new table now
        deltaTable = df.write.format("delta").mode("overwrite").save(table_path)
        print(deltaTable)

    def read(self, spark, table_path):
        return super().read(spark, table_path)
    
    def delete(self, spark, table_path, condition):
        return super().delete(spark, table_path, condition)
    
    def get_history(self, spark, table_path):
        return super().get_history(spark, table_path)
    
if __name__ == "__main__":
    # testing the client
    spark = get_spark()
    client = DeltaClient()

    # make a dataframe, write it to the S3, read it, update it, track history, delete it --> all in one go 
    data = [
        {"order_id": "ORD-0001", "status": "created", "amount": 450},
        {"order_id": "ORD-0002", "status": "created", "amount": 230},
        {"order_id": "ORD-0003", "status": "created", "amount": 200},
    ]

    df = spark.createDataFrame(data)

    # write the df into the data lake (S3)
    # new delta table 
    S3_location = "s3a://lakehouse/orders"
    client.write(df, S3_location, ["order_id"])