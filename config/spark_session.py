# This file is responsible for creating and returning a spark session based on the type: Delta, Hudi or Iceberg
# To load the respective JARs along with S3 configuration (actual S3 or minio) and return the SparkSession object that our client uses to interact with the underlying bucket 

# We are running this script inside the container, so it should point to the right container

from pyspark.sql import SparkSession
import os

# JAR packages required per format.
# These are downloaded from Maven Central the first time the session starts.
# Spark caches them locally after the first download.
#
# Format: "groupId:artifactId:version"
#
# NOTE: versions are tightly coupled to Spark 3.5.0 — do not change independently.
_PACKAGES = {
    "delta": ",".join([
        "io.delta:delta-spark_2.12:3.1.0",
        "org.apache.hadoop:hadoop-aws:3.3.4",
        "com.amazonaws:aws-java-sdk-bundle:1.12.262",
    ]),

    # Hudi and Iceberg will be added in Phase 4
    # "hudi":    "...",
    # "iceberg": "...",
}


# SQL extensions required per format.
# These enable format-specific SQL syntax inside Spark (e.g. DESCRIBE HISTORY for Delta).
_SQL_EXTENSIONS = {
    "delta": "io.delta.sql.DeltaSparkSessionExtension",
}


# Catalog implementations per format.
# The catalog tells Spark how to resolve table names and metadata.
_CATALOGS = {
    "delta": "org.apache.spark.sql.delta.catalog.DeltaCatalog",
}

# Resolve the enviroment variables

DATAENG_S3_URL=os.getenv("DATAENG_S3_URL", "http://minio:900") 
DATAENG_S3_ACCESS_KEY=os.getenv("DATAENG_S3_ACCESS_KEY", "minio@")
DATAENG_S3_SECRET_KEY=os.getenv("DATAENG_S3_SECRET_KEY", "minio123!")


def get_spark(format: str = "delta", app_name: str = "LocalLake") -> SparkSession:
    """
    Create and return a configured SparkSession for the given table format.

    The session is configured with:
      - The correct JARs for the requested format (downloaded from Maven Central)
      - MinIO as the S3-compatible object store (endpoint: http://minio:9000)
      - S3A filesystem settings for reading and writing s3a:// paths

    Args:
        format:   Table format to use. One of: "delta" (Phase 1),
                  "hudi" or "iceberg" (added in Phase 4).
        app_name: Name shown in the Spark UI for this session.

    Returns:
        A configured SparkSession instance.

    Usage:
        from config.spark_session import get_spark
        spark = get_spark(format="delta")

    To swap formats later (Phase 4), change only this one call:
        spark = get_spark(format="hudi")
    """
    if format not in _PACKAGES:
        raise ValueError(
            f"Unsupported format: '{format}'. "
            f"Available formats: {list(_PACKAGES.keys())}"
        )

    return (
        SparkSession.builder
        .appName(app_name)

        # --- JAR dependencies ---
        # Tells Spark which packages to download from Maven Central.
        # Downloaded once, then cached in ~/.ivy2 inside the container.
        .config("spark.jars.packages", _PACKAGES[format])

        # --- Format-specific SQL extensions ---
        # Enables Delta/Hudi/Iceberg specific SQL syntax.
        .config("spark.sql.extensions", _SQL_EXTENSIONS[format])

        # --- Catalog ---
        # Tells Spark how to resolve table names for this format.
        .config(
            "spark.sql.catalog.spark_catalog",
            _CATALOGS[format]
        )

        # --- MinIO / S3A configuration ---
        # These settings tell Spark how to talk to MinIO over the S3A protocol.
        # To switch to real AWS S3 later:
        #   1. Remove fs.s3a.endpoint
        #   2. Replace access.key + secret.key with IAM credentials
        #   3. Set path.style.access to false

        # Which S3A filesystem implementation to use
        .config(
            "spark.hadoop.fs.s3a.impl",
            "org.apache.hadoop.fs.s3a.S3AFileSystem"
        )

        # MinIO endpoint — points to the minio container on the Docker network.
        # Change to nothing (remove) when using real AWS S3.
        .config("spark.hadoop.fs.s3a.endpoint", DATAENG_S3_URL)

        # MinIO credentials (set in your docker-compose.yml)
        .config("spark.hadoop.fs.s3a.access.key", DATAENG_S3_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", DATAENG_S3_SECRET_KEY)

        # Path style access — required for MinIO.
        # MinIO uses: http://minio:9000/bucket/key  (path style)
        # AWS S3 uses: http://bucket.s3.amazonaws.com/key  (virtual hosted style)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")

        # Performance: how many times to retry a failed S3A request
        .config("spark.hadoop.fs.s3a.attempts.maximum", "1")

        # Performance: disable S3A's list v2 API — more compatible with MinIO
        .config("spark.hadoop.fs.s3a.list.version", "1")

        .getOrCreate()
    )

if __name__ == "__main__":
    # test function
    Session = get_spark("delta")
    print(Session)