import paho.mqtt.client as mqtt
import json
import time
import random

# 1. MQTT 연결 설정
broker_address = "localhost" # 내 컴퓨터
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Sensor_Simulator")
client.connect(broker_address, 1883)

print("📡 가짜 센서(ESP32) 가동 시작...")
print("   - 전송 데이터: CSI 파형 (128개 배열)")

while True:
    try:
        # 2. [핵심] 가짜 파형 데이터 생성 (128개 숫자 리스트)
        # 30~90 사이의 랜덤한 숫자 128개를 만듭니다.
        fake_wave = [random.randint(30, 90) for _ in range(128)]
        
        # 가끔 '낙상(FALL)' 상황 연출 (값이 갑자기 튀는 파형)
        current_label = "ADL"
        if random.randint(1, 10) > 8: # 20% 확률로 낙상 발생
            fake_wave = [random.randint(80, 150) for _ in range(128)] # 값이 확 커짐
            current_label = "FALL"

        # 3. 데이터 패킹 (JSON)
        # 'csi_value' (단일값) -> 'csi_data' (리스트)로 변경했습니다.
        data = {
            "device_id": "esp32_01",
            "csi_data": fake_wave,  
            "label": current_label,
            "timestamp": time.time()
        }

        # 4. JSON 변환 및 전송
        json_data = json.dumps(data)
        client.publish("ether-care/sensor", json_data)

        # 로그 출력 (너무 기니까 앞쪽 5개만 보여줌)
        print(f"📤 [전송] {current_label} | 데이터: {fake_wave[:5]}... (총 128개)")
        
        time.sleep(0.5) # 0.5초마다 전송

    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        time.sleep(1)