import paho.mqtt.client as mqtt
from influxdb import InfluxDBClient
import json
import math  # <--- [필수] 수학 계산용 모듈 추가!
import time

# ==========================================
# 1. InfluxDB 연결 설정
# ==========================================
db_client = InfluxDBClient(host='localhost', port=8086)
db_name = 'ether_db'

# DB가 없으면 생성 (get_list_database()는 dict 리스트를 반환하므로 이름만 뽑아서 비교)
existing_dbs = [db['name'] for db in db_client.get_list_database()]
if db_name not in existing_dbs:
    db_client.create_database(db_name)

db_client.switch_database(db_name)

# ==========================================
# 2. 메시지 수신 및 처리 함수
# ==========================================
def on_message(client, userdata, message):
    try:
        # JSON 포장 뜯기
        recv_str = message.payload.decode("utf-8")
        data = json.loads(recv_str)
        
        # 리스트 데이터 가져오기
        raw_wave = data.get("csi_data", []) 

        # [핵심 변경] 단순 평균(Mean) -> 표준편차(Std Dev)로 변경!
        # 표준편차는 데이터가 얼마나 "지랄맞게 움직이는지"를 나타냅니다.
        if len(raw_wave) > 0:
            # 1. 평균 구하기
            mean = sum(raw_wave) / len(raw_wave)
            # 2. 분산 구하기 (각 데이터가 평균에서 얼마나 떨어져 있나)
            variance = sum((x - mean) ** 2 for x in raw_wave) / len(raw_wave)
            # 3. 표준편차 (이 값을 저장하면 흔들 때 그래프 폭발함!)
            final_value = math.sqrt(variance)
        else:
            final_value = 0.0
            # 혹시 리스트가 아니라 단일 값이 오면 그냥 그걸 씀
            if isinstance(data.get("csi_value"), (int, float)):
                final_value = float(data["csi_value"])

        current_status = data.get("label", "ADL")
        device_id = data.get("device_id", "unknown")

        # DB 저장 포맷
        json_body = [
            {
                "measurement": "sensor_data_v2", # v2 유지 (중요!)
                "tags": {
                    "device": device_id,
                    "status": current_status
                },
                "fields": {
                    # 계산된 표준편차 값을 저장
                    "csi_value": float(final_value),
                    "packet_len": len(raw_wave) if isinstance(raw_wave, list) else 1
                }
            }
        ]
        
        # DB에 쓰기
        db_client.write_points(json_body)
        # 로그에 찍히는 값이 0.5 ~ 5.0 사이로 작게 나올 수 있지만, 흔들면 20~30까지 튈 겁니다.
        print(f"💾 [DB 저장] {device_id} | 상태: {current_status} | 변동성(표준편차): {final_value:.2f}")
        
    except Exception as e:
        print(f"❌ 데이터 처리 실패: {e}")
        print(f"   -> 받은 데이터: {message.payload}")

# ==========================================
# 3. MQTT 구독 시작
# ==========================================
try:
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "DB_Worker")
except AttributeError:
    mqtt_client = mqtt.Client("DB_Worker")

mqtt_client.subscribe("ether-care/sensor")
mqtt_client.on_message = on_message


def connect_with_retry(client, host, port, retries=5, delay=3):
    for attempt in range(1, retries + 1):
        try:
            client.connect(host, port)
            return
        except Exception as e:
            print(f"⚠️ MQTT 연결 실패 ({attempt}/{retries}): {e}")
            time.sleep(delay)
    raise ConnectionError(f"MQTT 브로커({host}:{port})에 연결할 수 없습니다.")


connect_with_retry(mqtt_client, "localhost", 1883)

print("🚀 DB 저장소 가동 (표준편차 모드 / sensor_data_v2)...")
mqtt_client.loop_forever()