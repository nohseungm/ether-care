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
| `web/` | 정적 프론트엔드 데모 페이지 (`index.html` 소개 페이지, `console.html` 모니터링 콘솔) — Cloudflare Pages 배포 대상 |

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

**낙상 recall 우선 임계값**: 기본 분류기는 fall recall이 0.71로 낮아(낙상의 약 30%를 못 잡음, 대부분 walk로 오인) 실서비스에는 위험합니다. 낙상을 놓치는 비용이 오탐 비용보다 크다고 보고, `features.py`의 `predict_with_fall_threshold()`로 fall 확률이 `FALL_THRESHOLD`(0.35) 이상이면 다른 클래스 확률이 더 높아도 fall로 판정하도록 했습니다. 그 결과 전체 정확도(90%대)는 그대로 유지하면서 fall recall만 0.71 → 0.83으로 올랐습니다. `train_model.py` 실행 시 일반 리포트와 이 임계값 적용 리포트를 함께 출력합니다.

**알려진 한계**: row_std/peak-to-peak 같은 통계량은 4개 클래스(fall/sit/walk/empty)의 평균·분산이 서로 거의 겹칠 정도로 약한 신호이고, 라벨별 데이터가 각각 단일 연속 녹화 세션 하나뿐이라 현재 수치는 그 세션 내에서의 시간순 분할 결과입니다. 즉 다른 사람/다른 환경/다른 날짜로 일반화된다는 보장은 아직 없습니다. 추가로 accuracy를 끌어올리려면 (1) 여러 사람·여러 세션·여러 환경에서 데이터를 더 모으고, (2) 1D-CNN/LSTM 등으로 원시 시계열 자체를 학습하는 방향이 더 근본적인 해법입니다.

### 4. 실시간 낙상 감지

```bash
python ai_model/realtime_predict.py
```

### 5. DB 저장 및 API 서버

```bash
python infra/save_to_db.py       # MQTT 데이터를 InfluxDB에 저장
uvicorn infra.api_server:app --reload   # /current-status API 제공
```

## 프론트엔드 데모 (`web/`)

- `web/index.html`: 서비스 소개 페이지 (와이파이 CSI 기반 낙상 감지 컨셉 설명).
- `web/console.html`: 실제 서비스 모니터링 콘솔 데모 — 사이드바로 전환되는 5개 화면(모니터링/신호 뷰어/이벤트 로그/알림/모델 리포트)으로 구성되며, 모델 리포트 화면의 정확도·recall·클래스별 지표는 위 `train_model.py` 실측치를 그대로 반영했습니다.
- 두 페이지 모두 정적 HTML/CSS/JS만으로 동작하며 별도 빌드 과정 없이 브라우저로 바로 열립니다. 외부 리소스는 Google Fonts, Tailwind Play CDN(`console.html`)만 사용합니다.
- 두 페이지는 상대 경로(`index.html` ↔ `console.html`)로 서로 링크되어 있어, 아래처럼 `web/`를 정적 사이트로 배포하면 그대로 작동합니다.

### Cloudflare Pages 배포 설정

Cloudflare Pages의 "Git에 연결" 흐름에서 아래 값을 그대로 입력하면 됩니다.

| 항목 | 값 |
|---|---|
| 프레임워크 프리셋 | `없음 (None)` |
| 빌드 명령 | *(비워둠)* — 정적 HTML이라 빌드 과정이 없음 |
| 빌드 출력 디렉터리 | `web` |
| 루트 디렉터리(고급) | `/` (기본값 그대로) |
| 환경 변수 | 필요 없음 |

배포되면 `https://ether-care.pages.dev/`가 `web/index.html`(소개 페이지)을, `https://ether-care.pages.dev/console.html`이 모니터링 콘솔을 보여줍니다.

## 참고

- `infra/influxdb_data/`, `infra/mosquitto/data/`, `infra/mosquitto/log/`는 런타임 중 생성되는 데이터로 버전관리 대상에서 제외되어 있습니다 (`.gitignore` 참고).
