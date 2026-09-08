import paho.mqtt.client as mqtt
import json
import joblib
import numpy as np # 계산용 라이브러리
import requests

# 1. AI 모델 로드
# (주의: 만약 에러가 나면, 모델이 '단일값' 전용이라서 그럴 수 있습니다.
# 일단은 로직 흐름만 잡아드립니다.)
try:
    model = joblib.load('fall_model.pkl')
    print("🧠 AI 모델 로드 완료!")
except:
    print("⚠️ 모델 파일이 없거나 호환되지 않습니다. (더미 모드로 동작)")
    model = None

# 디스코드 웹훅 주소 (대표님 거로 변경 필요)
DISCORD_URL = "YOUR_DISCORD_WEBHOOK_URL"

def send_alert(msg):
    try:
        requests.post(DISCORD_URL, json={"content": msg})
        print("🚨 디스코드 알림 전송 완료")
    except:
        pass

def on_message(client, userdata, message):
    try:
        recv_str = message.payload.decode("utf-8")
        data = json.loads(recv_str)
        
        # [핵심] 리스트 데이터 추출
        raw_wave = data["csi_data"]
        
        # AI 판단을 위한 특징 추출 (여기선 평균값을 사용)
        # 실제로는 128개를 다 넣어야 하지만, 지금 모델은 단순하므로 평균을 씁니다.
        avg_value = sum(raw_wave) / len(raw_wave)
        
        # --- AI 판단 로직 ---
        is_fall = False
        
        if model:
            # 모델이 있으면 물어보기 (평균값을 2D 배열로 변환해서 넣음)
            prediction = model.predict([[avg_value]])
            if prediction[0] == 1:
                is_fall = True
        else:
            # 모델 없으면 단순 규칙 (평균이 100 넘으면 낙상)
            if avg_value > 100:
                is_fall = True
        
        if is_fall:
            print(f"🚨 [위험] 낙상 감지! (신호세기: {avg_value:.1f})")
            send_alert(f"🚨 [경고] 거실에서 낙상이 감지되었습니다! (Signal: {avg_value:.1f})")
        else:
            print(f"✅ [정상] 활동 중 (Signal: {avg_value:.1f})")

    except Exception as e:
        print(f"❌ AI 처리 에러: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "AI_Guard")
client.connect("localhost", 1883)
client.subscribe("ether-care/sensor")
client.on_message = on_message

print("🤖 AI 보안관 가동 중...")
client.loop_forever()