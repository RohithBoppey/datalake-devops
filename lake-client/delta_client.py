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
        print(f"Data written into: {table_path} using S3 language")
        return deltaTable

    def read(self, spark, table_path):
        try: 
            df = DeltaTable.forPath(spark, table_path)
            return df
        except Exception as e:
            print("Error in reading the dataframe - ", e)
    
    def delete(self, spark, table_path, condition):
        try: 
            df = self.read(spark, table_path)
        except Exception as e: 
            print("Error in deleting the given dataframe: ", e)
            return
    
    def get_history(self, spark, table_path):
        try: 
            # only history is present for a delta table 
            if not DeltaTable.isDeltaTable(spark, table_path): 
                raise RuntimeError("history only exists for a delta table")

            # now is a delta table which must have history
            delta_table = self.read(spark, table_path)
            history_df = delta_table.history(limit=100)
            return history_df

        except Exception as e: 
            print("Error in retrieving history: ", e)
    
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
    spark = df.sparkSession 

    print("df created: \n", df)

    # write the df into the data lake (S3)
    # new delta table 
    S3_location = "s3a://lakehouse/orders"
    client.write(df, S3_location, ["order_id"])

    # now reading the read dataframe
    df = client.read(spark, S3_location)
    df.toDF().show(5)

    # now make an update operation to that df and write in incrementally 
    # adding a new few records
    new_data = [{"order_id": "ORD-0004", "status": "created", "amount": 999}]
    new_df = spark.createDataFrame(new_data)

    # merge with our new table for the update operation
    (
    df.alias("target")
        .merge(
            new_df.alias("source"),
            "target.order_id = source.order_id"
        )
        .whenNotMatchedInsertAll()
        .execute()
    )
    print("DF updated - new record added")
    df.toDF().show(5)

    # finally delete the table
    df.delete("amount < 1000")  # guarantees all data is being deleted

    final_df = client.read(spark, S3_location)
    final_df.toDF().show(5)

    # at this point, it should record in history
    # now the history should retrieve all the operations done on this delta table 
    history_df = client.get_history(spark, S3_location)
    history_df.show(10)


    # all are done
    print("All functions are working properly")