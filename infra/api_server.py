from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # <--- [핵심] CORS 라이브러리
from influxdb import InfluxDBClient
import json

# 1. 앱 생성
app = FastAPI()

# 2. [CORS 설정] 외부(팀원 B의 웹사이트) 접속 허용
# 이 부분이 없으면 방화벽을 뚫어도 'Network Error'가 뜹니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 모든 주소(*)에서의 접속을 허용
    allow_credentials=False,  # "*"와 credentials=True는 브라우저가 거부하는 조합이라 비활성화
    allow_methods=["*"],      # 모든 HTTP 메소드(GET, POST 등) 허용
    allow_headers=["*"],      # 모든 헤더 허용
)

# 3. DB 연결 설정
db_client = InfluxDBClient(host='localhost', port=8086)
db_name = 'ether_db'

try:
    existing_dbs = [db['name'] for db in db_client.get_list_database()]
    if db_name not in existing_dbs:
        db_client.create_database(db_name)
except Exception as e:
    # InfluxDB가 아직 안 떠 있어도 서버 자체는 죽지 않고 뜨도록 함
    print(f"⚠️ [경고] InfluxDB 연결/DB 생성 확인 실패: {e}")

db_client.switch_database(db_name)

@app.get("/")
def read_root():
    return {"message": "Ether-Care API Server is Running!"}

# 팀원 B가 호출할 주소
@app.get("/current-status")
def get_current_status():
    try:
        # DB에서 가장 최신 데이터 1개 가져오기 (시간 역순 정렬)
        result = db_client.query('SELECT * FROM sensor_data_v2 ORDER BY time DESC LIMIT 1')
        points = list(result.get_points())

        if not points:
            # 데이터가 아직 없을 때
            return {
                "status": "Waiting...",
                "value": 0,
                "timestamp": "No Data"
            }

        latest = points[0]
        
        # DB에 저장된 값 꺼내서 팀원 B에게 주기
        return {
            "timestamp": latest['time'],
            "status": latest['status'],   # ADL 또는 FALL
            "value": latest['csi_value'], # 평균값 (그래프 그리기용)
            "device": latest['device']
        }

    except Exception as e:
        return {"error": str(e)}

# (참고) 실행은 이 파일 안에서 하는 게 아니라 
# boot.bat 또는 터미널에서 'uvicorn ...' 명령어로 합니다.