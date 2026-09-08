import paho.mqtt.client as mqtt

# 데이터가 들어오면 실행되는 함수 (자동 실행)
def on_message(client, userdata, message):
    # 깨진 문자열을 예쁘게 디코딩해서 출력
    recv_data = message.payload.decode("utf-8")
    print(f"📥 [서버 수신완료] {recv_data}")

# 서버 연결 설정
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "Monitor_Admin")
client.connect("localhost", 1883)

# "이 채널을 구독하겠다" 선언
client.subscribe("ether-care/sensor")

# 메시지 수신 함수 연결
client.on_message = on_message

print("👀 데이터 감시 중... (대기 모드)")
# 프로그램 끄지 말고 계속 기다려라
client.loop_forever()