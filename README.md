# EFK Stack — Bài thực hành 1

Môi trường thực hành thu thập và xem Docker logs bằng Elasticsearch, Fluentd và Kibana. Elasticsearch và Kibana được ghim ở phiên bản `7.17.0`; hai ứng dụng mẫu phát log JSON định kỳ qua Docker Fluentd logging driver.

## 1. Kiến trúc

```text
api-one ─┐
         ├─ Docker logging driver (Fluentd, async) ─> Fluentd :24224
api-two ─┘                                             │
                                                     │ HTTP :9200
                                                     v
                                               Elasticsearch
                                                     ^
                                                     │ HTTP :9200
                                                   Kibana
```

Compose tạo network riêng `efk`. Elasticsearch và Kibana chỉ publish lên loopback máy host (`127.0.0.1`). Docker Engine gửi log đến Fluentd qua cổng host `24224`; Fluentd chuyển log vào Elasticsearch theo định dạng index `quickbite-YYYY.MM.DD`. Data Elasticsearch và file buffer Fluentd được lưu trong named volumes.

## 2. Cấu trúc thư mục

```text
EFK-Stack/
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── fluentd/
│   ├── Dockerfile
│   ├── fluent.conf
│   └── plugins/
│       └── Gemfile
├── logstash/
│   ├── Dockerfile
│   ├── pipeline/
│   │   └── logstash.conf
│   └── test_logstash.py
├── spring-boot-demo/
│   ├── Dockerfile
│   ├── pom.xml
│   ├── test_load.py
│   └── src/main/
│       ├── java/com/storex/demo/
│       └── resources/
│           ├── application.properties
│           └── logback-spring.xml
└── app/
    ├── Dockerfile
    └── app.py
```

## 3. Yêu cầu

- Docker Desktop hoặc Docker Engine với Docker Compose v2.
- Đủ RAM cho Docker. Elasticsearch dùng heap mặc định `512 MiB`; có thể đổi `ES_JAVA_OPTS` trong `.env` nếu máy có đủ bộ nhớ.
- Cổng host `9200`, `5601`, `24224` chưa bị ứng dụng khác sử dụng.

### `vm.max_map_count`

Trên Linux, Elasticsearch yêu cầu ít nhất `262144`. Kiểm tra và đặt tạm thời:

```bash
sudo sysctl vm.max_map_count
sudo sysctl -w vm.max_map_count=262144
```

Để giữ thiết lập sau khi khởi động lại, thêm `vm.max_map_count=262144` vào `/etc/sysctl.conf`, rồi áp dụng:

```bash
sudo sysctl -p
```

Trên Windows/macOS với Docker Desktop, Elasticsearch chạy trong Linux VM/WSL2. Thiết lập sysctl của Windows không thay thế thiết lập trong Linux VM; các phiên bản Docker Desktop hiện hành thường đã đặt giá trị phù hợp. Nếu Elasticsearch báo `vm.max_map_count ... is too low`, hãy cập nhật Docker Desktop, khởi động lại Docker Desktop/WSL2 và kiểm tra lại trong môi trường Linux mà Docker Engine sử dụng. Không cần thêm `sysctls` không được hỗ trợ vào service Compose.

## 4. Cấu hình môi trường

`.env` hiện chứa các giá trị mặc định không nhạy cảm. Nó đã được loại khỏi Git; giữ `.env.example` để tham khảo khi tạo môi trường mới:

```dotenv
ES_JAVA_OPTS=-Xms512m -Xmx512m
APP_LOG_INTERVAL_SECONDS=5
LOGSTASH_JAVA_OPTS=-Xms256m -Xmx256m
```

## 5. Khởi động

Chạy tại thư mục chứa `docker-compose.yml`:

```bash
docker compose config
docker compose up -d --build
```

Lần đầu Docker cần tải image và build Fluentd cùng ứng dụng mẫu; thời gian khởi động có thể lâu hơn. Không dùng `docker compose down -v` nếu muốn giữ dữ liệu.

## 6. Kiểm tra services và logs

```bash
docker compose ps -a
docker compose logs
docker compose logs -f elasticsearch
docker compose logs -f fluentd
docker compose logs -f api-one api-two
curl http://localhost:9200
```

Elasticsearch healthcheck chờ cluster tối thiểu ở trạng thái `yellow`; Kibana có healthcheck qua `/api/status`, Fluentd kiểm tra cổng forward `24224`. Ứng dụng mẫu lần lượt phát `INFO`, `WARN`, `ERROR` và thêm `service.name` vào từng JSON log event.

Với cụm Elasticsearch chỉ có một node, index mặc định có thể ở trạng thái `yellow` vì replica không thể được phân bổ sang node thứ hai. Đây là trạng thái bình thường của cấu hình single-node; hãy kiểm tra healthcheck và truy vấn log thay vì yêu cầu index phải `green`.

## 7. Kibana và tìm kiếm log

Mở [http://localhost:5601](http://localhost:5601). Sau khi Kibana hoàn tất khởi động:

1. Mở **Stack Management → Data Views** (tùy phiên bản giao diện có thể hiện **Index Patterns**) và chọn tạo Data View.
2. Đặt tên/index pattern là `quickbite-*`.
3. Chọn `@timestamp` làm **Timestamp field**, rồi lưu.
4. Mở **Discover**, chọn Data View `quickbite-*` và khoảng thời gian bao gồm thời điểm vừa chạy ứng dụng.
5. Dùng KQL để lọc, ví dụ:

```text
service.name : "api-one"
```

```text
level : "ERROR"
```

```text
service.name : "api-two" and level : "WARN"
```

Các trường `level` và `service.name` được gửi trong JSON của ứng dụng. Trường `docker_tag` do Fluentd thêm vào để lưu tag `quickbite.api-one` hoặc `quickbite.api-two`.

## 8. Dừng và xóa dữ liệu

Dừng và xóa containers/network nhưng giữ named volumes:

```bash
docker compose down
```

Chỉ khi thực sự muốn xóa dữ liệu Elasticsearch và buffer Fluentd mới chạy:

```bash
docker compose down -v
```

Lệnh thứ hai xóa các named volumes của project và không thể khôi phục dữ liệu đã xóa.

## 9. Lỗi thường gặp

- **Elasticsearch không khởi động / `vm.max_map_count` quá thấp:** đặt giá trị host Linux thành `262144` như phần trên; với Docker Desktop, cập nhật/khởi động lại Docker Desktop hoặc WSL2.
- **Cổng đã được sử dụng:** giải phóng cổng `9200`, `5601` hoặc `24224`, hoặc đổi cổng host ở phía bên trái dấu hai chấm trong Compose. Nếu đổi cổng host Fluentd, hãy cập nhật `fluentd-address` ở cả hai ứng dụng.
- **Kibana chưa sẵn sàng:** chờ healthcheck hoàn tất và kiểm tra `docker compose logs -f elasticsearch kibana`. Xác nhận `ELASTICSEARCH_HOSTS` trỏ đến `http://elasticsearch:9200` — cổng HTTP nội bộ của Compose, không phải `9300`.
- **Fluentd không khả dụng hoặc không thấy log:** kiểm tra `docker compose ps -a`, `docker compose logs -f fluentd`, cổng host `24224` và healthcheck Fluentd. Logging driver của ứng dụng đã bật `fluentd-async: "true"`.
- **Elasticsearch chưa có index:** chờ vài giây để Fluentd flush buffer, kiểm tra log Fluentd và hoạt động của `api-one`/`api-two`; sau đó xác nhận khoảng thời gian Discover và Data View `quickbite-*`.
- **Thiếu bộ nhớ:** giảm heap `ES_JAVA_OPTS` trong `.env` (ví dụ `-Xms256m -Xmx256m`) hoặc cấp thêm RAM cho Docker.

> Docker `fluentd` logging driver gửi log container tới Fluentd. Tùy thiết lập dual logging của Docker Engine, `docker compose logs api-one` có thể không hiển thị log; hãy kiểm tra sự kiện ứng dụng trong Kibana và tình trạng nhận log trong Fluentd.

## 10. Bài thực hành 2 — Logstash nhận log TCP từ Spring Boot

### Mục tiêu và luồng dữ liệu

Bài thực hành này bổ sung Logstash 7.17.0 vào network Compose hiện có. Ứng dụng Spring Boot gửi mỗi log JSON trên một dòng qua TCP đến `localhost:5000`; Logstash parse sự kiện, in bản ghi đã parse ra stdout và gửi đến Elasticsearch. Dữ liệu bài 1 qua Fluentd vẫn chạy độc lập.

```text
Spring Boot -- TCP :5000 / JSON Lines --> Logstash
                                            ├── stdout (rubydebug)
                                            └── HTTP :9200 --> Elasticsearch
                                                               └── Kibana
```

Port `5000` chỉ bind trên loopback host. Trong container network, Logstash kết nối Elasticsearch bằng hostname `elasticsearch` và HTTP port `9200`.

### `json_lines` và pipeline

File [logstash.conf](./logstash/pipeline/logstash.conf) cấu hình input TCP trên cổng `5000` với `codec => json_lines`. Mỗi sự kiện phải là một JSON object hợp lệ kết thúc bằng newline (`\n`). Codec giải mã JSON thành các trường event độc lập, ví dụ `service`, `level`, `message` và `order_id`, không lưu cả JSON thành một chuỗi.

Pipeline của bài 2 ban đầu ghi vào index `storex-logs-%{+YYYY.MM.dd}`. Sau bài 3, cấu hình hiện tại định tuyến động theo `app_name`; output `stdout` vẫn dùng `rubydebug` để xem trường đã parse. Script `test_logstash.py` gửi `app_name: storex-backend`, nên ở cấu hình hiện tại event vào `storex-backend-YYYY.MM.dd`. Heap Logstash mặc định là `256 MiB` trong `.env`; điều chỉnh `LOGSTASH_JAVA_OPTS` nếu cần.

### Khởi động Logstash

Từ thư mục project:

```bash
docker compose config
docker compose up -d --build
docker compose ps -a
docker compose logs -f logstash
```

Compose chờ Elasticsearch healthcheck trước khi khởi động Logstash. Lần đầu có thể cần tải image/build và chờ Logstash nạp pipeline. Kiểm tra cổng TCP trên Windows:

```powershell
Test-NetConnection localhost -Port 5000
```

### Gửi JSON kiểm thử

Đã có script [test_logstash.py](./logstash/test_logstash.py). Chạy bằng Python trên host:

```bash
python logstash/test_logstash.py
```

Nếu Python chưa được cài trên host, có thể chạy script từ container Python trên cùng network Compose:

```bash
docker run --rm --network efk-stack_efk \
  -e LOGSTASH_HOST=logstash \
  -v "$PWD/logstash:/test:ro" \
  python:3.12-slim python /test/test_logstash.py
```

Biến `LOGSTASH_HOST` mặc định là `localhost` cho lần chạy từ host; khi chạy trong network Compose, dùng `logstash`.

Script gửi sự kiện mẫu dưới đây, kèm newline bắt buộc:

```json
{"app_name":"storex-backend","service":"storex-backend","level":"INFO","message":"Order created successfully","order_id":1001}
```

Có thể gửi một sự kiện khác bằng Python:

```python
import json
import socket

data = {
    "app_name": "storex-backend",
    "service": "storex-backend",
    "level": "INFO",
    "message": "Order created successfully",
    "order_id": 1001,
}

with socket.create_connection(("localhost", 5000)) as sock:
    sock.sendall((json.dumps(data) + "\n").encode("utf-8"))
```

Ứng dụng Spring Boot cần cấu hình appender TCP gửi JSON Lines (mỗi JSON event một dòng) tới host `localhost`, port `5000` khi chạy trên host; nếu chạy trong Compose, dùng hostname `logstash`, port `5000`. Không gửi JSON nhiều dòng nếu chưa cấu hình framing tương ứng.

### Kiểm tra Elasticsearch và Kibana

Sau khi gửi test event, kiểm tra index và document:

```bash
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/storex-backend-*/_search?pretty"
```

Trong kết quả `_source`, xác nhận `service`, `level`, `message`, `order_id` là các trường riêng. Kiểm tra Logstash stdout để thấy event parse:

```bash
docker compose logs --tail=100 logstash
```

Trong [Kibana](http://localhost:5601), vào **Stack Management → Data Views**, tạo Data View `storex-backend-*`, chọn `@timestamp` làm trường thời gian, rồi mở **Discover** để xem sự kiện. Nếu chưa thấy dữ liệu, mở rộng khoảng thời gian chọn trong Discover.

### Lỗi thường gặp

- **Cổng `5000` đang được sử dụng:** dừng ứng dụng đang chiếm cổng hoặc đổi host port trong Compose; nếu đổi port container thì đồng thời sửa `port` trong `logstash.conf`.
- **Logstash không khởi động / pipeline lỗi:** kiểm tra `docker compose logs logstash`, YAML bằng `docker compose config` và cú pháp pipeline trong `logstash.conf`.
- **Không có document trong Elasticsearch:** xác nhận Elasticsearch healthy, Logstash cùng network `efk`, output host là `http://elasticsearch:9200`, và chờ pipeline flush/ghi index.
- **Document chứa JSON nguyên chuỗi hoặc không có trường:** gửi đúng một JSON object trên mỗi dòng, kết thúc bằng `\n`, và kiểm tra input `codec => json_lines`.
- **Không thấy document trong Kibana:** xác nhận Data View là `storex-logs-*`, trường thời gian `@timestamp` và khoảng thời gian Discover bao gồm lúc gửi test event.

## 11. Bài thực hành 3 — Phân loại log theo service

### Mục tiêu và dynamic index

Logstash chọn index Elasticsearch theo trường `app_name` của từng JSON event. Cấu hình trong [logstash.conf](./logstash/pipeline/logstash.conf):

```text
index => "%{[app_name]}-%{+YYYY.MM.dd}"
```

- `%{[app_name]}` là sprintf field reference của Logstash: giá trị trường `app_name` trong event được dùng làm phần tên index, không cần hardcode từng ứng dụng trong output.
- `%{+YYYY.MM.dd}` tạo phần ngày từ `@timestamp` của event, ví dụ `2026.11.03`.
- Vì vậy log `user-service` và `order-service` trong cùng pipeline được ghi lần lượt vào `user-service-2026.11.03` và `order-service-2026.11.03`.

Pipeline chuẩn hóa `app_name` thành chữ thường và thay ký tự không hợp lệ bằng dấu `-`, để tên index tuân thủ quy tắc Elasticsearch. Nếu trường bị thiếu hoặc rỗng, giá trị mặc định là `unknown-service`; các tên bắt đầu bằng `_` hoặc `-` được chuẩn hóa để không tạo tên index không hợp lệ. Giá trị đã chuẩn hóa vẫn được lưu trong document.

### Chạy cấu hình và kiểm thử

Từ thư mục project, kiểm tra Compose rồi khởi động lại Logstash để nạp pipeline đã mount:

```bash
docker compose config
docker compose restart logstash
docker compose ps -a
docker compose logs --tail=100 logstash
```

Chạy script kiểm thử trên host:

```bash
python logstash/test_index_routing.py
```

Script gửi lần lượt bốn JSON Lines events (mỗi event kết thúc bằng `\n`): hai cho `user-service` và hai cho `order-service`. Nếu Python chưa có trên host, chạy script trong container ứng dụng đang nằm trên network Compose:

```powershell
docker cp .\logstash\test_index_routing.py efk-stack-api-one-1:/tmp/test_index_routing.py
docker exec -e LOGSTASH_HOST=logstash efk-stack-api-one-1 python /tmp/test_index_routing.py
```

Khi chạy script từ chính host, không cần đặt `LOGSTASH_HOST`; giá trị mặc định là `localhost`. Từ một container trong network Compose phải đặt `LOGSTASH_HOST=logstash`.

### Xác minh Elasticsearch

Chờ vài giây để Logstash ghi event, sau đó xem indices và từng nhóm:

```bash
curl "http://localhost:9200/_cat/indices?v"
curl "http://localhost:9200/user-service-*/_search?pretty"
curl "http://localhost:9200/order-service-*/_search?pretty"
```

Kết quả cần có hai index ngày hiện tại, `user-service-YYYY.MM.dd` và `order-service-YYYY.MM.dd`. Mỗi index cần chứa hai document thuộc đúng service, với `app_name`, `level`, `message` và trường ID riêng (`user_id` hoặc `order_id`) được parse thành các trường có cấu trúc. Trường `app_name` không được xóa khỏi event.

### Xem trong Kibana

Mở [Kibana](http://localhost:5601), vào **Stack Management → Data Views** và tạo hai Data View:

1. `user-service-*`, chọn `@timestamp` làm trường thời gian.
2. `order-service-*`, chọn `@timestamp` làm trường thời gian.

Mở **Discover**, chọn Data View cần kiểm tra và đặt khoảng thời gian bao gồm lúc chạy script. KQL có thể lọc `app_name : "user-service"` hoặc `level : "ERROR"`.

### Lỗi thường gặp

- **Cả hai service vẫn vào index cũ:** xem `docker compose logs --tail=100 logstash`, xác nhận pipeline được mount vào `/usr/share/logstash/pipeline/logstash.conf`, rồi chạy `docker compose restart logstash`.
- **Tên index không hợp lệ hoặc event vào `unknown-service`:** bảo đảm JSON có `app_name` không rỗng; pipeline chuẩn hóa ký tự và dùng `unknown-service` khi trường thiếu/rỗng.
- **Chỉ một index được tạo:** gửi ít nhất một event cho mỗi `app_name`, đảm bảo mỗi JSON kết thúc bằng newline và chờ Logstash ghi dữ liệu.
- **Không thấy document:** xác nhận input TCP port `5000`, Logstash đang chạy, Elasticsearch healthy và kiểm tra đúng ngày/index pattern.
- **Không thấy log trong Kibana:** tạo Data View riêng cho từng pattern ở trên, chọn `@timestamp` và mở rộng time range.

## 12. Bài thực hành 4 — Hạn chế ảnh hưởng khi Logstash nghẽn

### Mục tiêu và nguyên nhân log bị mất/chậm

Module demo Spring Boot tại `spring-boot-demo/` gửi JSON TCP đến Logstash (`logstash:5000`) và được Logstash định tuyến vào index `storex-backend-YYYY.MM.dd`. Maven chọn Spring Boot `3.2.4` (Java 17, Logback `1.4.x`) và `logstash-logback-encoder` `7.4`, phiên bản encoder tương thích Logback 1.3/1.4.

Khi đích TCP chậm hoặc ngắt, thao tác ghi log có thể bị chậm do buffer đầy, reconnect hoặc backpressure. Nếu request xử lý log ngay trên luồng nghiệp vụ, việc chờ có thể làm tăng latency. Mạng TCP cũng không đồng nghĩa với việc event đã được xác nhận ghi bền vững vào Elasticsearch.

```text
Trực tiếp:   request thread -> LogstashTcpSocketAppender -> TCP -> Logstash -> Elasticsearch
Bất đồng bộ: request thread -> AsyncAppender queue -> TCP appender -> TCP -> Logstash -> Elasticsearch
```

### AsyncAppender và trade-off

`logback-spring.xml` mặc định dùng Spring profile `async`; profile `direct` giữ cấu hình so sánh. Trong profile `async`, root logger tham chiếu `ASYNC_LOGSTASH`, không gọi appender TCP trực tiếp.

- `queueSize=8192`: số sự kiện chờ tối đa trong hàng đợi Logback; bộ nhớ thực tế phụ thuộc kích thước event. Đây không phải giới hạn bytes và không phải hàng đợi bền vững.
- `discardingThreshold=0`: tắt việc chủ động loại bỏ sớm các log mức thấp khi hàng đợi còn ít chỗ. Khi hàng đợi đầy, event mới vẫn có thể bị loại vì `neverBlock=true`.
- `neverBlock=true`: producer không chờ để thêm event khi queue đã đầy; request ít bị ảnh hưởng hơn nhưng log có thể bị mất.
- `maxFlushTime=3000`: khi ứng dụng shutdown bình thường, AsyncAppender chờ tối đa 3000 ms để consumer xử lý queue. Đây không phải cam kết flush khi process bị kill, máy mất điện hoặc quá trình gửi TCP chưa được Elasticsearch xác nhận.
- `LogstashTcpSocketAppender` cũng có cơ chế gửi nền/buffer riêng; AsyncAppender bổ sung queue ở phía ứng dụng. Hai lớp buffer không tạo ra bảo đảm lưu trữ bền vững.

Ba mục tiêu cần phân biệt: **không block ứng dụng**, **không mất log**, và **log được lưu bền vững**. Cấu hình này ưu tiên giảm block; queue đầy, process dừng đột ngột, lỗi mạng hoặc Logstash/Elasticsearch từ chối dữ liệu vẫn có thể làm mất event. Nếu yêu cầu audit/financial cần giao nhận tin cậy, cân nhắc broker/persistent queue có disk, xác nhận/retention phù hợp và cơ chế retry/quan sát được. Cần đo tải thực tế ở mức mục tiêu 10.000 events/giây; cấu hình demo không tự bảo đảm throughput đó.

### Chạy ứng dụng và kiểm tra API

Compose thêm service `storex-backend` vào network `efk`, publish API trên `127.0.0.1:18080` (cổng host `8080` đã được một dịch vụ khác sử dụng trên máy này) và kết nối Logstash bằng tên DNS `logstash`.

```bash
docker compose config
docker compose up -d --build storex-backend
docker compose ps -a
docker compose logs -f storex-backend
```

Có thể chạy module ngoài Docker với JDK 17+ và Maven:

```bash
cd spring-boot-demo
mvn test
mvn spring-boot:run
```

Gửi một request kiểm tra các mức INFO/WARN/ERROR:

```bash
curl -i http://localhost:18080/test-log
```

Tạo batch log có giới hạn:

```bash
curl -i "http://localhost:18080/generate-logs?count=10000"
```

`count` mặc định là `10000`, hợp lệ từ `1` đến `20000`; giá trị ngoài giới hạn trả HTTP 400. Mỗi request có `request_id` (cũng trả về header `X-Request-Id`); encoder thêm `app_name=storex-backend` và `@timestamp` vào event JSON.

### Đo latency API

Script `spring-boot-demo/test_load.py` đo tổng thời gian, latency trung bình, số request thành công/thất bại. Ví dụ gửi 1000 request với tối đa 20 worker:

```bash
python spring-boot-demo/test_load.py --requests 1000 --concurrency 20
```

Nếu host chưa cài Python, chạy script trong container ứng dụng mẫu trên cùng Compose network:

```powershell
docker cp .\spring-boot-demo\test_load.py efk-stack-api-one-1:/tmp/test_load.py
docker exec efk-stack-api-one-1 python /tmp/test_load.py --url http://storex-backend:8080/test-log --requests 100 --concurrency 5
```

Có thể chạy batch sinh 1000 log, 10 lần để giới hạn tổng tải:

```bash
python spring-boot-demo/test_load.py --url "http://localhost:18080/generate-logs?count=1000" --requests 10 --concurrency 4
```

Script giới hạn số request (50.000), concurrency (100) và có timeout để không chạy vô hạn. Concurrency là số client; Spring Boot có giới hạn thread riêng nên kết quả cần được diễn giải theo cấu hình máy.

### So sánh direct và async, mô phỏng Logstash ngắt kết nối

`async` là cấu hình mặc định. Để tạm chuyển sang appender TCP trực tiếp khi so sánh trong PowerShell:

```powershell
docker compose stop logstash
$env:STOREX_LOGGING_PROFILE = "direct"
docker compose up -d --no-deps --force-recreate storex-backend
Remove-Item Env:STOREX_LOGGING_PROFILE
python spring-boot-demo/test_load.py --requests 100 --concurrency 5
```

Sau đó khởi động lại ứng dụng ở chế độ AsyncAppender và khôi phục Logstash:

```powershell
$env:STOREX_LOGGING_PROFILE = "async"
docker compose up -d --no-deps --force-recreate storex-backend
Remove-Item Env:STOREX_LOGGING_PROFILE
docker compose start logstash
python spring-boot-demo/test_load.py --requests 100 --concurrency 5
```

Chỉ dừng service Logstash demo; không dừng Elasticsearch/Kibana, không xóa volumes. So sánh thời gian phản hồi, tỷ lệ thành công và log nhận được sau khi Logstash hoạt động lại. Giữ batch nhỏ khi thử direct mode; tăng tải chỉ trong môi trường thử nghiệm. Không chạy ngập 10.000 events/giây trên máy cá nhân để kết luận về production. Khi queue đầy, profile async loại event mới thay vì block producer; direct mode bỏ outer queue nhưng TCP appender vẫn có buffer và hành vi riêng. Đây là minh họa trade-off, không phải bảo đảm không mất log.

AsyncAppender queue không có metric endpoint bật trong demo. Để quan sát queue khi benchmark, cần bật/thu thập Logback JMX hoặc thêm instrumentation/metrics có kiểm soát; không nên suy ra queue còn chỗ chỉ từ HTTP status.

### Xem dữ liệu và hạn chế

Logstash output theo `app_name`, do đó mở [Kibana](http://localhost:5601), tạo Data View `storex-backend-*` với `@timestamp`, rồi dùng Discover. Có thể kiểm tra trực tiếp:

```bash
curl "http://localhost:9200/storex-backend-*/_search?pretty"
docker compose logs --tail=100 logstash
```

Event cần có `app_name`, `@timestamp`, `level`, `message` và MDC `request_id`. Trong lần shutdown bình thường, `maxFlushTime` giới hạn thời gian chờ; khi queue đã đầy với `neverBlock=true`, sự kiện bị rơi có thể không xuất hiện trong Elasticsearch. Muốn bảo đảm bền vững hơn cần buffer/transport có persistence và chính sách xác nhận, không chỉ thêm AsyncAppender.
