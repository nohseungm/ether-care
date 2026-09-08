import paho.mqtt.client as mqtt
import json
import joblib
import pandas as pd
import warnings
import os
import sys
import time

# 자잘한 경고 숨기기
warnings.filterwarnings("ignore")

# -----------------------------------
# [1] 순정 모델 경로 설정
# -----------------------------------
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ether_care_model.pkl")

if not os.path.exists(MODEL_PATH):
    print("❌ [에러] 모델 없음! train_model.py를 먼저 실행하세요.")
    sys.exit()

print("========================================")
print("🧠 실시간 감지 AI (순정 미인 모드) 로딩 중...")
model = joblib.load(MODEL_PATH)
print("✅ 로딩 완료! 감지 시작 (종료: Ctrl + C)")
print("========================================")


def predict_action(client, userdata, message):
    try:
        payload = message.payload.decode("utf-8")
        data = json.loads(payload)
        raw_wave = data.get("csi_data", [])

        if len(raw_wave) == 128:
            # 🌟 필터나 묶음(Window) 없이 들어온 날것 그대로 바로 예측!
            df = pd.DataFrame([raw_wave], columns=[f"csi_{i}" for i in range(128)])
            prediction = model.predict(df)[0]

            # 결과 출력
            if prediction == "fall":
                print("🚨 [위험] 낙상 감지 (FALL) 🚨")
            elif prediction == "sit":
                print("🪑 [안전] 앉음 (SIT)")
            elif prediction == "walk":
                print("🚶 [활동] 걷기 (WALK)")
            elif prediction == "empty":
                print("👻 [비었음] 공백 (EMPTY)")

    except Exception:
        pass

    # MQTT 통신 연결 설정


try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "AI_Predictor")
except AttributeError:
    client = mqtt.Client("AI_Predictor")


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
client.on_message = predict_action

# 무한 감지 실행
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\n========================================")
    print("🛑 [종료] 실시간 감지를 안전하게 종료합니다.")
    print("========================================")
    client.disconnect()