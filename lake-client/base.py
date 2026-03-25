# This file contains the interface required to be implemented by the following clients for interacting with the delta lake: 
# - Delta Lake
# - Hudi 
# - Iceberg

# List of functions

from abc import ABC, abstractmethod
from pyspark.sql import DataFrame, SparkSession


class LakeTableClient(ABC):
    """
    Abstract interface for interacting with a lake table format.
    Implementations: DeltaLakeClient, HudiClient, IcebergClient.

    To swap formats, change only the instantiation line in your pipeline:
        client = DeltaLakeClient()   ->   client = HudiClient()
    """

    @abstractmethod
    def write(self, df: DataFrame, table_path: str, key_cols: list[str]) -> None:
        """
        Upsert records into the table.

        - If the table does not exist yet, creates it (INSERT).
        - If a record with the same key_cols already exists, updates it (UPDATE).
        - If a record with the same key_cols does not exist, inserts it (INSERT).

        Args:
            df:         Spark DataFrame containing the records to write.
            table_path: S3A path to the table, e.g. "s3a://lakehouse/orders".
            key_cols:   List of column names that uniquely identify a record,
                        e.g. ["order_id"]. Used to match existing rows for upsert.
        """
        ...

    @abstractmethod
    def read(self, spark: SparkSession, table_path: str) -> DataFrame:
        """
        Read the current snapshot of the table as a Spark DataFrame.

        Always returns a consistent, fully committed view of the data.
        Partially written batches or in-flight transactions are never visible.

        Args:
            spark:      Active SparkSession.
            table_path: S3A path to the table, e.g. "s3a://lakehouse/orders".

        Returns:
            Spark DataFrame representing the latest state of the table.
        """
        ...

    @abstractmethod
    def delete(self, spark: SparkSession, table_path: str, condition: str) -> None:
        """
        Delete all rows from the table that match the given SQL condition.

        The delete is recorded as a new version in the transaction log.
        Deleted rows remain visible via get_history() for time travel,
        but are excluded from all subsequent read() calls.

        Args:
            spark:      Active SparkSession.
            table_path: S3A path to the table, e.g. "s3a://lakehouse/orders".
            condition:  SQL WHERE clause string identifying rows to delete,
                        e.g. "order_id = 'ORD-0001'" or "status = 'cancelled'".
        """
        ...

    @abstractmethod
    def get_history(self, spark: SparkSession, table_path: str) -> DataFrame:
        """
        Return the full transaction history of the table.

        Each row in the returned DataFrame represents one committed operation
        (write, delete, schema change, etc.) with its version number, timestamp,
        and operation details.

        Enables:
          - Auditing: see every change ever made to the table.
          - Time travel: use version numbers to read the table as of a past state.
          - Incremental reads: find what changed since a given version (used by Flink).

        Args:
            spark:      Active SparkSession.
            table_path: S3A path to the table, e.g. "s3a://lakehouse/orders".

        Returns:
            Spark DataFrame with one row per committed transaction.
        """
        ...