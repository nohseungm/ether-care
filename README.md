# Ether-Care

Wi-Fi CSI(Channel State Information) 신호를 이용해 낙상(fall) 여부를 실시간으로 감지하는 시스템입니다. 센서 장치가 MQTT로 CSI 파형을 전송하면, AI 모델이 이를 `fall` / `sit` / `walk` / `empty` 중 하나로 분류하고 결과를 DB에 저장한 뒤 API로 외부에 제공합니다.

## 아키텍처

```
센서(CSI 송신 장치)
      │  MQTT publish (topic: ether-care/sensor)
      ▼
Mosquitto (MQTT 브로커, infra/mosquitto)
      │
      ├─▶ ai_model/realtime_predict.py  ── 실시간 낙상 감지 (콘솔 출력)
      │
      └─▶ infra/save_to_db.py           ── 변동성(표준편차) 계산 후 InfluxDB 저장
                                                │
                                                ▼
                                        InfluxDB (infra/influxdb_data)
                                                │
                                                ▼
                                infra/api_server.py (FastAPI, /current-status)
                                                │
                                                ▼
                                        Grafana / 외부 웹 클라이언트
```

## 폴더 구조

| 경로 | 설명 |
|---|---|
| `ai_model/` | 학습 데이터 수집, 모델 학습, 실시간 예측 스크립트 및 학습된 모델(`.pkl`) |
| `infra/` | MQTT 브로커, InfluxDB, FastAPI API 서버 설정 및 실행 코드 (`docker-compose.yml`) |
| `data/` | 라벨별 학습용 CSV 데이터 (`fall`, `sit`, `walk`, `empty`) |
| `archive_tests/` | 초기 프로토타입 및 테스트용 스크립트 |

## 준비 사항

- Python 3.x
- Docker / Docker Compose
- Python 패키지: `paho-mqtt`, `influxdb`, `pandas`, `scikit-learn`, `joblib`, `fastapi`, `uvicorn`

## 실행 방법

### 1. 인프라 기동 (MQTT, InfluxDB, Grafana)

```bash
cd infra
docker-compose up -d
```

### 2. 학습 데이터 수집 (선택)

`ai_model/collect_data.py`의 `CURRENT_LABEL` 값을 `fall` / `sit` / `walk` / `empty` 중 하나로 지정한 뒤 실행하면, MQTT로 들어오는 CSI 데이터를 `data/ether_care_data_standard/`에 CSV로 저장합니다.

```bash
python ai_model/collect_data.py
```

### 3. 모델 학습

```bash
python ai_model/train_model.py
```

`data/ether_care_data_standard/`의 CSV들을 읽어 RandomForest 분류기를 학습하고, `ai_model/ether_care_model.pkl`로 저장합니다.

특징(feature)은 `ai_model/features.py`의 `FeatureExtractor`에서 계산하며, 학습(`train_model.py`)과 실시간 추론(`realtime_predict.py`)이 동일한 로직을 공유합니다. 원본 128개 CSI 값에 더해, 단기(8프레임)·장기(30프레임) 이동 윈도우의 표준편차/피크투피크(peak-to-peak) 통계를 함께 사용합니다 — 낙상은 짧은 순간의 스파이크, 걷기는 지속적인 중간 크기 변동이라는 차이를 잡아내기 위함입니다. 시간순 분할(각 라벨 녹화의 마지막 20%를 시험 데이터로 사용) 기준 정확도는 **90.29%**입니다 (기존 순정 단일 프레임 방식은 동일 기준 87.17%).

### 4. 실시간 낙상 감지

```bash
python ai_model/realtime_predict.py
```

### 5. DB 저장 및 API 서버

```bash
python infra/save_to_db.py       # MQTT 데이터를 InfluxDB에 저장
uvicorn infra.api_server:app --reload   # /current-status API 제공
```

## 참고

- `infra/influxdb_data/`, `infra/mosquitto/data/`, `infra/mosquitto/log/`는 런타임 중 생성되는 데이터로 버전관리 대상에서 제외되어 있습니다 (`.gitignore` 참고).
