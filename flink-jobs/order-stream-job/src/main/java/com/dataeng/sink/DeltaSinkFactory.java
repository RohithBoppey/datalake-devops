package com.dataeng.sink;

import io.delta.flink.sink.DeltaSink;
import org.apache.flink.core.fs.Path;
import org.apache.flink.table.data.RowData;
import org.apache.flink.table.types.logical.RowType;
import org.apache.hadoop.conf.Configuration;

public class DeltaSinkFactory {

    // config variables
    private static final String S3A_ENDPOINT = "http://minio:9000";
    private static final String S3A_ACCESS_KEY = "minio";
    private static final String S3A_SECRET_KEY = "minio123";

    /**
     * Create a DeltaSink configured for MinIO/S3A.
     *
     * @param tablePath S3A path to the Delta table, e.g. "s3a://lakehouse/orders"
     * @param rowType   Flink RowType describing the schema of the rows being written
     * @return a configured DeltaSink ready to attach to a DataStream
     */
    public static DeltaSink<RowData> createDeltaSink(String tablePath, RowType rowType) {
        Configuration hadoopConf = new Configuration();
        hadoopConf.set("fs.s3a.endpoint", S3A_ENDPOINT);
        hadoopConf.set("fs.s3a.access.key", S3A_ACCESS_KEY);
        hadoopConf.set("fs.s3a.secret.key", S3A_SECRET_KEY);
        hadoopConf.set("fs.s3a.path.style.access", "true");
        hadoopConf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem");

        return DeltaSink
                .forRowData(new Path(tablePath), hadoopConf, rowType)
                .build();
    }
}
