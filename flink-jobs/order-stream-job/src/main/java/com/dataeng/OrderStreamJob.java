package com.dataeng;

import com.dataeng.deserializer.OrderEventDeserializer;
import com.dataeng.model.OrderEvent;
import com.dataeng.sink.DeltaSinkFactory;

import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.table.data.GenericRowData;
import org.apache.flink.table.data.RowData;
import org.apache.flink.table.data.StringData;
import org.apache.flink.table.types.logical.DoubleType;
import org.apache.flink.table.types.logical.RowType;
import org.apache.flink.table.types.logical.VarCharType;

import java.util.Arrays;

public class OrderStreamJob {

    private static final String KAFKA_BROKERS = "kafka:9092";
    private static final String KAFKA_TOPIC = "orders";
    private static final String CONSUMER_GROUP = "flink-order-consumer";

    private static final String ACTIVE_TABLE_PATH = "s3a://lakehouse/orders";
    private static final String CANCELLED_TABLE_PATH = "s3a://lakehouse/orders_cancelled";

    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Checkpointing required by DeltaSink for exactly-once writes
        env.enableCheckpointing(30_000);

        // Kafka source
        KafkaSource<OrderEvent> kafkaSource = KafkaSource.<OrderEvent>builder()
                .setBootstrapServers(KAFKA_BROKERS)
                .setTopics(KAFKA_TOPIC)
                .setGroupId(CONSUMER_GROUP)
                .setStartingOffsets(OffsetsInitializer.earliest())
                .setDeserializer(new OrderEventDeserializer())
                .build();

        DataStream<OrderEvent> orderStream = env.fromSource(
                kafkaSource,
                WatermarkStrategy.noWatermarks(),
                "Kafka Orders"
        );

        // Define the RowType (schema) for Delta
        RowType rowType = new RowType(Arrays.asList(
                new RowType.RowField("order_id", new VarCharType()),
                new RowType.RowField("status", new VarCharType()),
                new RowType.RowField("amount", new DoubleType()),
                new RowType.RowField("updated_at", new VarCharType())
        ));

        // Split: active orders vs cancelled orders
        DataStream<RowData> activeStream = orderStream
                .filter(e -> !e.getStatus().equals("cancelled"))
                .map(OrderStreamJob::toRowData);

        DataStream<RowData> cancelledStream = orderStream
                .filter(e -> e.getStatus().equals("cancelled"))
                .map(OrderStreamJob::toRowData);

        // Attach Delta sinks
        activeStream.sinkTo(DeltaSinkFactory.createDeltaSink(ACTIVE_TABLE_PATH, rowType));
        cancelledStream.sinkTo(DeltaSinkFactory.createDeltaSink(CANCELLED_TABLE_PATH, rowType));

        env.execute("Order Stream Job");
    }

    private static RowData toRowData(OrderEvent event) {
        GenericRowData row = new GenericRowData(4);
        row.setField(0, StringData.fromString(event.getOrderId()));
        row.setField(1, StringData.fromString(event.getStatus()));
        row.setField(2, event.getAmount());
        row.setField(3, StringData.fromString(event.getUpdatedAt()));
        return row;
    }
}
