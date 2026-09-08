import pandas as pd
import glob
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

# -----------------------------------
# [1] 기본 경로 설정
# -----------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "..", "data", "ether_care_data_standard")  # 데이터 폴더 경로
MODEL_PATH = os.path.join(_BASE_DIR, "ether_care_model.pkl")  # AI 모델 저장 경로


def train():
    print("========================================")
    print("🧠 [AI 학습 시스템] 순정(Raw) 데이터 모드 시작")
    print("========================================")

    # 지정 폴더 내 모든 CSV 파일 검색
    all_files = glob.glob(os.path.join(DATA_DIR, "training_data_*.csv"))

    # 파일 누락 시 에러 처리
    if not all_files:
        print("❌ [에러] CSV 파일 없음!")
        return

    df_list = []

    # 찾은 파일들 순차적으로 읽기
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            if df.empty: continue  # 빈 파일 무시
            df_list.append(df)

            # 파일명에서 행동 라벨 추출 및 출력
            label = os.path.basename(filename).replace("training_data_", "").replace(".csv", "")
            print(f"   - 읽기 완료: {label} ({len(df)}줄)")
        except Exception:
            pass

    # 읽은 파일이 전부 비어있으면 학습 불가
    if not df_list:
        print("❌ [에러] 유효한 데이터가 없음! (CSV가 전부 비어있음)")
        return

    # 읽은 데이터 하나의 데이터프레임으로 병합
    full_data = pd.concat(df_list, ignore_index=True)

    # 🌟 필터링 없이 원본 전파 데이터(X) 그대로 사용
    X = full_data.filter(like="csi_")

    # 정답 라벨(y) 추출
    y = full_data["label"]

    # 훈련용(80%) 및 시험용(20%) 데이터 분할
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("\n🤖 AI 두뇌 학습 중... (생얼 미인 모드)")

    # 랜덤 포레스트 분류기 생성 및 학습
    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    # 시험 데이터로 예측 진행
    y_pred = model.predict(X_test)

    # 최종 정확도 계산
    acc = accuracy_score(y_test, y_pred)

    print("\n========================================")
    print(f"🎓 최종 시험 점수: {acc * 100:.2f}% (87% 복구 목표!)")
    print("========================================")

    # 행동별 상세 채점 결과 출력
    print(classification_report(y_test, y_pred))

    # 학습 완료된 모델 파일로 저장
    joblib.dump(model, MODEL_PATH)
    print("💾 [저장 완료] 순정 모델 저장 완료!")


if __name__ == "__main__":
    train()