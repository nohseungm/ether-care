import paho.mqtt.client as mqtt
import json
import csv
import os
import time
from datetime import datetime

# ==========================================
# 🎯 [1] 행동 설정 (저장하기 전에 여기만 바꾸세요!)
# "fall" (넘어짐) / "walk" (걷기) / "sit" (앉기)
# ==========================================
CURRENT_LABEL = "fall"
# ==========================================

# ==========================================
# 📂 [2] 저장 경로 설정 (폴더 자동 생성)
# =========================================
BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "ether_care_data_standard"
)

# 폴더가 없으면 자동으로 만듭니다! (걱정 NO)
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)
    print(f"✨ [알림] '{BASE_DIR}' 폴더를 새로 만들었습니다!")

# 파일명: ether_care_data/training_data_fall.csv
FILENAME = os.path.join(BASE_DIR, f"training_data_{CURRENT_LABEL}.csv")

# 파일 헤더(제목) 작성
if not os.path.exists(FILENAME):
    with open(FILENAME, mode='w', newline='') as file:
        writer = csv.writer(file)
        header = ["timestamp", "label"] + [f"csi_{i}" for i in range(128)]
        writer.writerow(header)
    print(f"📝 [신규 파일] 생성 완료: {FILENAME}")
else:
    print(f"📂 [이어 쓰기] 기존 파일에 추가합니다: {FILENAME}")

def save_csv(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)
        raw_wave = data.get("csi_data", []) 
        
        if len(raw_wave) > 0:
            with open(FILENAME, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([datetime.now().strftime("%H:%M:%S"), CURRENT_LABEL] + raw_wave)
            
            # 보기 좋게 로그 출력
            print(f"💾 [{CURRENT_LABEL}] 데이터 {len(raw_wave)}개 저장 중... (Ctrl+C로 종료)")
            
    except Exception as e:
        print(f"❌ 에러: {e}")

# MQTT 연결
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "DataCollector")
except AttributeError:
    client = mqtt.Client("DataCollector")


def connect_with_retry(client, host, port, retries=5, delay=3):
    for attempt in range(1, retries + 1):
        try:
            client.connect(host, port)
            return
        except Exception as e:
            print(f"⚠️ MQTT 연결 실패 ({attempt}/{retries}): {e}")
            time.sleep(delay)
    raise ConnectionError(f"MQTT 브로커({host}:{port})에 연결할 수 없습니다.")


connect_with_retry(client, "localhost", 1883)
client.subscribe("ether-care/sensor")
client.on_message = save_csv

print(f"\n========================================")
print(f"🎥 [촬영 준비 완료] 저장 위치:")
print(f"👉 {FILENAME}")
print(f"🛑 다 찍으면 [Ctrl + C]를 눌러서 저장하고 끄세요!")
print(f"========================================\n")

client.loop_forever()