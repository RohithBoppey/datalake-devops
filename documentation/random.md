Running a golang container: 

```
docker run -it --rm \
  --network host \
  -v /Users/rohithboppey/Documents/golang-deps \
  golang:latest \
  bash
```