package com.dataeng.deserializer;

import com.dataeng.model.OrderEvent;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.apache.flink.api.common.serialization.DeserializationSchema;
import org.apache.flink.api.common.typeinfo.TypeInformation;
import org.apache.flink.connector.kafka.source.reader.deserializer.KafkaRecordDeserializationSchema;
import org.apache.flink.util.Collector;
import org.apache.kafka.clients.consumer.ConsumerRecord;

import java.io.IOException;

public class OrderEventDeserializer implements KafkaRecordDeserializationSchema<OrderEvent> {

    private transient ObjectMapper objectMapper;

    @Override
    public void open(DeserializationSchema.InitializationContext context) {
        objectMapper = new ObjectMapper();
    }

    @Override
    public void deserialize(ConsumerRecord<byte[], byte[]> record, Collector<OrderEvent> out)
            throws IOException {
        if (objectMapper == null) {
            objectMapper = new ObjectMapper();
        }
        OrderEvent event = objectMapper.readValue(record.value(), OrderEvent.class);
        out.collect(event);
    }

    @Override
    public TypeInformation<OrderEvent> getProducedType() {
        return TypeInformation.of(OrderEvent.class);
    }
}
