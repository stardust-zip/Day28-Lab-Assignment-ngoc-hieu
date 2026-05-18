# Hướng Dẫn Nộp Bài - Lab #28: Full Platform Integration Sprint

## Yêu Cầu Nộp Bài

**Full AI infrastructure platform demo** - từ data ingestion đến model serving với full observability.

## Các Artifacts Cần Nộp

### 1. Source Code

- Folder `lab28/` hoàn chỉnh với tất cả files
- Tất cả integration scripts hoạt động
- Prefect flows đã deploy và schedule

### 2. Screenshots Demo

Chụp màn hình các bước:

- Prefect UI: http://localhost:4200 (flow đang chạy)
- API Gateway call: `curl http://localhost:8000/health`
- Grafana dashboard: http://localhost:3000

### 3. Kết Quả Smoke Tests

Chạy và chụp màn hình kết quả:

```bash
cd lab28
pytest smoke-tests/ -v
```

Kỳ vọng: 5/5 tests passing

### 4. Production Readiness Score

```bash
python scripts/production_readiness_check.py
```

Kỳ vọng: Score >80%

### 5. Documentation

- `README.md` giải thích cách:
  - Start platform: `docker compose up -d`
  - Deploy Prefect flows
  - Run smoke tests
  - Access dashboards (Grafana:3000, Prometheus:9090, Prefect:4200)

## Định Dạng Nộp Bài

Tạo Repo GitHub chứa:

```
lab28_submission_[student_id]
├── lab28/                    # Source code hoàn chỉnh
│   ├── docker-compose.yml
│   ├── prefect/flows/
│   ├── scripts/
│   ├── api-gateway/
│   └── monitoring/
├── screenshots/              # Screenshots demo
│   ├── prefect_ui.png
│   ├── api_gateway.png
│   └── grafana_dashboard.png
├── smoke_tests_results.png   # Screenshot kết quả pytest
├── production_readiness.png  # Screenshot readiness score
└── README.md                # Hướng dẫn setup
```

## Địa Điểm Nộp

Nộp link repo GitHub qua LMS

## Tiêu Chí Chấm Điểm

| Tiêu Chí                 | Trọng Số | Mô Tả                                                        |
| ------------------------ | -------- | ------------------------------------------------------------ |
| Integration Completeness | 40%      | Tất cả 10 integration points hoạt động, data flow end-to-end |
| Observability            | 25%      | Logs, metrics, traces hiển thị; alerts configured            |
| Performance              | 20%      | Latency trong SLO; load tested; không có memory leaks        |
| Architecture Quality     | 15%      | Clean separation, GitOps config, documented decisions        |

## Các Vấn Đề Cần Tránh

- Config drift giữa các environments
- Thiếu error handling tại integration points
- Monitoring coverage không hoàn chỉnh
- Không có rollback strategy
- Demo không test trước khi nộp

## 5 Câu Hỏi Cần Trả Lời Khi Nộp

1. **Phân tích các trade-offs trong thiết kế kiến trúc AI platform của bạn. Bạn đã cân bằng giữa performance, reliability, và maintainability như thế nào?**

2. **Trong kiến trúc hybrid (Local + Kaggle), bạn xử lý ngắt kết nối giữa local và Kaggle như thế nào? Có cơ chế fallback không?**

3. **Giải thích cách event-driven architecture với Kafka giúp decouple các components trong AI platform của bạn.**

4. **Bạn đã implement observability như thế nào? Logs, metrics, và traces được thu thập và visualized ra sao?**

5. **Nếu một service trong stack (ví dụ: Qdrant hoặc Kafka) bị crash, hệ thống của bạn sẽ xử lý như thế nào? Có graceful degradation không?**

## Câu Hỏi Thêm?

Liên hệ giảng viên qua LMS hoặc office hours.

---

## Trả Lời 5 Câu Hỏi

### Câu 1: Phân tích trade-offs trong thiết kế kiến trúc

**Kiến trúc tổng thể:** Hybrid Local (Docker Compose) + Kaggle (GPU).

| Tiêu chí            | Lựa chọn                                                                | Trade-off                                                                                                                                                                                                                          |
| ------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Performance**     | vLLM + Qdrant (vector search) + ngrok tunneling                         | Qdrant với COSINE distance cho RAG giúp inference nhanh hơn (top-3 context). Ngrok gây latency (~50-100ms) nhưng cho phép dùng GPU mạnh trên Kaggle. Timeout API Gateway 1s đảm bảo response nhanh, đánh đổi bằng fallback answer. |
| **Reliability**     | Fallback trong `api-gateway/main.py` (try-except bắt mọi Exception)     | Nếu LLM call fail, trả về hardcoded answer + `model: "fallback"`. Hy sinh accuracy nhưng đảm bảo service luôn online.                                                                                                              |
| **Maintainability** | Docker Compose single-file, Prometheus + Grafana, Prefect orchestration | Dễ reproduce (`docker compose up`), nhưng không có Kubernetes cho auto-scaling. Volume mount cho Prefect worker thay vì build image riêng — tiện cho dev nhưng kém production-ready.                                               |

**Cân bằng:** Ưu tiên reliability và maintainability hơn peak performance — phù hợp lab/demo. Production sẽ thêm K8s, circuit breaker, và multi-region deployment.

---

### Câu 2: Xử lý ngắt kết nối Local ↔ Kaggle

**Cơ chế fallback** trong `api-gateway/main.py`:

```python
try:
    async with httpx.AsyncClient(timeout=1) as client:
        llm_resp = await client.post(f"{VLLM_URL}/v1/chat/completions", ...)
    answer = result["choices"][0]["message"]["content"]
    model = result["model"]
except Exception:
    answer = "Platform engineering is the practice of designing and building software delivery platforms."
    model = "fallback"
```

- **Phát hiện disconnect:** Exception catch-all — bất kỳ lỗi nào (timeout, connection refused, DNS failure) đều được bắt.
- **Fallback behavior:** Trả về câu trả lời mặc định + đánh dấu `model: "fallback"` để client biết đây là degraded response.
- **Health check vẫn hoạt động:** Endpoint `/health` độc lập, không bị ảnh hưởng bởi Kaggle.
- **Hạn chế:** Chưa có retry mechanism, circuit breaker, hay queue cho requests khi Kaggle offline. Có thể cải thiện bằng exponential backoff hoặc failover sang model local nhẹ hơn.

---

### Câu 3: Event-driven architecture với Kafka

Kafka đóng vai trò **backbone message broker** giúp decouple các component:

```
Producer (scripts/01_ingest_to_kafka.py)
    → Kafka topic "data.raw"
        → Prefect flow (prefect/flows/kafka_to_delta.py)
            → Delta Lake (Parquet)
                → Feast/Redis (scripts/03_delta_to_feast.py)
        → Embedding service (Kaggle)
            → Qdrant (scripts/05_embed_to_qdrant.py)
```

**Lợi ích cụ thể:**

1. **Temporal decoupling:** Producer không cần đợi consumer xử lý xong. Script ingest gửi data lên Kafka và kết thúc ngay.
2. **Spatial decoupling:** Consumer (Prefect flow) chạy riêng biệt, có thể scale độc lập, không ảnh hưởng producer.
3. **Buffer & durability:** Kafka persist messages, nếu consumer down, data không mất — có thể replay khi consumer上线.
4. **Parallel pipelines:** Cùng một message có thể được consume bởi nhiều consumer groups (Delta Lake pipeline + Embedding pipeline).
5. **Fault isolation:** Nếu Qdrant crash, data vẫn an toàn trong Kafka, không ảnh hưởng đến data ingestion.

---

### Câu 4: Implement observability

**Ba trụ cột observability:**

| Trụ cột     | Công cụ              | Cấu hình                                                                                                                                                                                                   |
| ----------- | -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Metrics** | Prometheus + Grafana | `prometheus_fastapi_instrumentator` expose `/metrics` tự động. Prometheus scrape qua `monitoring/prometheus.yml` với 3 jobs: api-gateway, kafka, prefect-orion. Grafana dashboard visualize tại port 3000. |
| **Traces**  | LangSmith            | LangSmith client tracking project `lab28-platform`. Kiểm tra bằng `scripts/09_verify_observability.py` — `client.list_runs(project_name="lab28-platform")`.                                                |
| **Logs**    | Docker logs + stdout | Prefect flow in ra console (`print(f"Consumed {len(records)} records")`), API Gateway dùng print, Docker tự capture stdout.                                                                                |

**Kiểm tra production readiness** (`scripts/production_readiness_check.py`): 9 checks bao gồm health endpoint, Prometheus up, Grafana up, metrics endpoint, unauthorized rejection, Qdrant health, Redis reachability, Kafka topics.

**Smoke tests** (`smoke-tests/test_e2e.py`): `TestObservability` kiểm tra Prometheus scrape (`up{job='api-gateway'} == 1`) và Grafana accessibility.

---

### Câu 5: Graceful degradation khi service crash

| Service crash     | Cơ chế xử lý                                                                                                                                                                                           | Mức độ ảnh hưởng                                                                                                  |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| **Qdrant**        | API Gateway gọi Qdrant bằng httpx. Nếu Qdrant down → HTTP exception → không có context → LLM vẫn trả lời nhưng không có RAG context.                                                                   | Partial degradation — mất context retrieval nhưng vẫn trả lời, chất lượng giảm.                                   |
| **Kafka**         | Data ingestion từ Kafka bị lỗi. Prefect flow có timeout 5s (`consumer_timeout_ms=5000`), trả về records rỗng → `save_to_delta` kiểm tra `if not records: print("No records to save")` → graceful skip. | Data pipeline tạm dừng, không crash toàn hệ thống. API Gateway không phụ thuộc Kafka nên inference vẫn hoạt động. |
| **vLLM (Kaggle)** | Try-except trong API Gateway → fallback answer + `model: "fallback"`.                                                                                                                                  | Full degradation — mất LLM inference, chỉ trả hardcoded answer. Health check vẫn 200.                             |
| **Redis/Feast**   | Redis dùng làm feature store. Nếu down, feature retrieval fail. API Gateway có `REDIS_URL` env nhưng không hard-depend trong inference path.                                                           | Mất feature enrichment, không ảnh hưởng core inference.                                                           |

**Thiết kế tổng thể:** Mỗi component hoạt động độc lập, không có hard dependency chain. API Gateway là điểm duy nhất user-facing và luôn trả response 200 nhờ fallback. Health endpoint hoàn toàn độc lập nên monitoring luôn hoạt động.
