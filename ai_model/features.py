from collections import deque

import numpy as np

CSI_LEN = 128
WIN_SHORT = 8
WIN_LONG = 30

CSI_COLUMNS = [f"csi_{i}" for i in range(CSI_LEN)]
WINDOW_COLUMNS = [
    f"win{WIN_SHORT}_std_max", f"win{WIN_SHORT}_std_mean",
    f"win{WIN_SHORT}_ptp_max", f"win{WIN_SHORT}_ptp_mean",
    f"win{WIN_LONG}_std_max", f"win{WIN_LONG}_std_mean",
    f"win{WIN_LONG}_ptp_max", f"win{WIN_LONG}_ptp_mean",
    "row_std", "row_ptp", "spike_ratio",
]
FEATURE_COLUMNS = CSI_COLUMNS + WINDOW_COLUMNS


class FeatureExtractor:
    """CSI 프레임을 (원본 128값 + 단기/장기 변동성 윈도우 통계) 벡터로 변환.

    낙상은 짧은 순간의 큰 스파이크, 걷기는 지속적인 중간 크기 변동이라는
    차이를 잡아내기 위해 row_std/row_ptp의 단기(WIN_SHORT)·장기(WIN_LONG)
    이동 통계를 함께 사용한다. 학습(train_model.py)과 실시간 추론
    (realtime_predict.py) 양쪽에서 반드시 이 클래스를 통해서만 특징을
    계산해야 두 경로의 계산이 어긋나지 않는다.
    """

    def __init__(self, win_short=WIN_SHORT, win_long=WIN_LONG):
        self.win_short = win_short
        self.win_long = win_long
        self.std_buf = deque(maxlen=win_long)
        self.ptp_buf = deque(maxlen=win_long)

    def transform(self, raw_wave):
        raw = np.asarray(raw_wave, dtype=float)
        row_std = float(raw.std())
        row_ptp = float(raw.max() - raw.min())

        self.std_buf.append(row_std)
        self.ptp_buf.append(row_ptp)
        std_arr = np.fromiter(self.std_buf, dtype=float)
        ptp_arr = np.fromiter(self.ptp_buf, dtype=float)

        def window_stats(arr, w):
            recent = arr[-w:]
            return float(recent.max()), float(recent.mean())

        std_max_s, std_mean_s = window_stats(std_arr, self.win_short)
        ptp_max_s, ptp_mean_s = window_stats(ptp_arr, self.win_short)
        std_max_l, std_mean_l = window_stats(std_arr, self.win_long)
        ptp_max_l, ptp_mean_l = window_stats(ptp_arr, self.win_long)
        spike_ratio = ptp_max_s / (ptp_mean_l + 1e-6)

        return list(raw) + [
            std_max_s, std_mean_s, ptp_max_s, ptp_mean_s,
            std_max_l, std_mean_l, ptp_max_l, ptp_mean_l,
            row_std, row_ptp, spike_ratio,
        ]

    def reset(self):
        self.std_buf.clear()
        self.ptp_buf.clear()
