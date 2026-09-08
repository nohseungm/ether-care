import paho.mqtt.client as mqtt
import json

# AI의 판단 기준 (임계값)
THRESHOLD = 80

def analyze_data(client, userdata, message):
    try:
        # 1. 데이터 까보기
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)
        current_value = data["csi_value"]
        
        # 2. AI 판단 (Rule-based)
        if current_value >= THRESHOLD:
            print(f"🚨 [경고] 낙상 감지됨!! (값: {current_value}) -> 보호자에게 알림 전송!")
            # 나중에는 여기서 진짜 문자를 보내거나 사이렌을 울립니다.
        else:
            print(f"✅ [안전] 정상 범위입니다. (값: {current_value})")
            
    except Exception as e:
        print("에러:", e)

# 연결 설정
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "AI_Guard")
client.connect("localhost", 1883)
client.subscribe("ether-care/sensor") # 센서 데이터 구독
client.on_message = analyze_data

print("🤖 AI 감시 시스템 가동... (낙상을 잡아냅니다)")
client.loop_forever()