Upon up-ing the container from the kafka setup yaml file: 

command: 
`docker exec -it dataeng_devops-kafka-1 bash`

Test creating a topic: 

```
kafka-topics --create \
  --topic test-topic \
  --bootstrap-server localhost:9092 \
  --partitions 1 \
  --replication-factor 1
```

```
kafka-console-producer \
  --topic test-topic \
  --bootstrap-server localhost:9092
```

```
kafka-console-consumer \
  --topic test-topic \
  --from-beginning \
  --bootstrap-server localhost:9092
```