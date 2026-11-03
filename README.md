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
