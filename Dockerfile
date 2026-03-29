FROM apache/spark:3.5.0

# Switch to root to install packages
USER root

# Install Python dependencies
# delta-spark version must match Spark version:
# Spark 3.5.x -> delta-spark 3.1.0
RUN pip install --no-cache-dir \
    delta-spark==3.1.0 \
    boto3==1.34.0 \
    pyspark==3.5.0

# Switch back to the default spark user for security
USER spark