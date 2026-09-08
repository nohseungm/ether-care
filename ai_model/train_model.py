import pandas as pd
import glob
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

from features import FeatureExtractor, FEATURE_COLUMNS, CSI_COLUMNS

# -----------------------------------
# [1] 기본 경로 설정
# -----------------------------------
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "..", "data", "ether_care_data_standard")  # 데이터 폴더 경로
MODEL_PATH = os.path.join(_BASE_DIR, "ether_care_model.pkl")  # AI 모델 저장 경로

TEST_RATIO = 0.2  # 각 라벨 파일의 마지막 20%를 시험 데이터로 사용 (시간순 분할)


def featurize_file(df):
    extractor = FeatureExtractor()
    rows = [extractor.transform(row) for row in df[CSI_COLUMNS].to_numpy(dtype=float)]
    feat = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    feat["label"] = df["label"].values
    return feat


def train():
    print("========================================")
    print("🧠 [AI 학습 시스템] 윈도우 특징 강화 모드 시작")
    print("========================================")

    # 지정 폴더 내 모든 CSV 파일 검색
    all_files = glob.glob(os.path.join(DATA_DIR, "training_data_*.csv"))

    # 파일 누락 시 에러 처리
    if not all_files:
        print("❌ [에러] CSV 파일 없음!")
        return

    train_parts, test_parts = [], []

    # 찾은 파일들 순차적으로 읽기 (파일 = 하나의 연속 녹화 세션이므로,
    # 파일 경계를 넘어 시간축 특징이 섞이지 않도록 파일 단위로 처리)
    for filename in all_files:
        try:
            df = pd.read_csv(filename)
            if df.empty: continue  # 빈 파일 무시

            feat = featurize_file(df)
            cut = int(len(feat) * (1 - TEST_RATIO))
            train_parts.append(feat.iloc[:cut])
            test_parts.append(feat.iloc[cut:])

            # 파일명에서 행동 라벨 추출 및 출력
            label = os.path.basename(filename).replace("training_data_", "").replace(".csv", "")
            print(f"   - 읽기 완료: {label} ({len(df)}줄)")
        except Exception:
            pass

    # 읽은 파일이 전부 비어있으면 학습 불가
    if not train_parts:
        print("❌ [에러] 유효한 데이터가 없음! (CSV가 전부 비어있음)")
        return

    train_df = pd.concat(train_parts, ignore_index=True)
    test_df = pd.concat(test_parts, ignore_index=True)

    X_train, y_train = train_df[FEATURE_COLUMNS], train_df["label"]
    X_test, y_test = test_df[FEATURE_COLUMNS], test_df["label"]

    print("\n🤖 AI 두뇌 학습 중... (단기/장기 변동성 윈도우 특징 반영)")

    # 랜덤 포레스트 분류기 생성 및 학습 (fall/walk처럼 헷갈리는 클래스를
    # 위해 class_weight로 소수 클래스 가중치 보정)
    model = RandomForestClassifier(n_estimators=150, random_state=42, class_weight="balanced")
    model.fit(X_train, y_train)

    # 시험 데이터로 예측 진행
    y_pred = model.predict(X_test)

    # 최종 정확도 계산
    acc = accuracy_score(y_test, y_pred)

    print("\n========================================")
    print(f"🎓 최종 시험 점수: {acc * 100:.2f}% (시간순 분할, 87% 복구 목표!)")
    print("========================================")

    # 행동별 상세 채점 결과 출력
    print(classification_report(y_test, y_pred))

    # 학습 완료된 모델 파일로 저장
    joblib.dump(model, MODEL_PATH)
    print("💾 [저장 완료] 윈도우 특징 모델 저장 완료!")


if __name__ == "__main__":
    train()
