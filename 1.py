# -*- coding: utf-8 -*-
"""
建立 FFOCT 主觀評分系統用 manifest.csv

目前資料設定：
- 部位：face、hand
- face：10 cases
- hand：10 cases
- 每個 case 有 5 種影像來源：SSOCT、CycleGAN、FUSRGAN、OUR、FFOCT
- 總影像數：20 cases × 5 methods = 100 張

輸出：
G:\\app\\rating_dataset\\manifest.csv

manifest 會隨機打亂影像順序，並重新編碼為 Image_001 ~ Image_100。
"""

import os
import random
import pandas as pd


# =========================
# 路徑設定
# =========================
DATASET_ROOT = r"G:\app\rating_dataset"
OUTPUT_CSV = os.path.join(DATASET_ROOT, "manifest.csv")

# 固定隨機種子，確保每次產生的順序一致
RANDOM_SEED = 1208

# 支援圖片副檔名
VALID_EXT = [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]

# 五種要評分的影像來源
METHODS = ["SSOCT", "CycleGAN", "FUSRGAN", "OUR", "FFOCT"]

# =========================
# 資料設定：face 10、hand 10
# =========================
REGIONS = {
    "face": {
        "folder": "face",
        "count": 10,
        "name_patterns": {
            "SSOCT": [
                "SSOCT{n}", "ssoct{n}",
                "SSOCTface{n}", "ssoctface{n}"
            ],
            "CycleGAN": [
                "cycleganface{n}", "CycleGANface{n}",
                "cyclegan{n}", "CycleGAN{n}"
            ],
            "FUSRGAN": [
                "fusrganface{n}", "FUSRGANface{n}",
                "fusrgan{n}", "FUSRGAN{n}"
            ],
            "OUR": [
                "ourface{n}", "OURface{n}",
                "our{n}", "OUR{n}"
            ],
            "FFOCT": [
                "FFOCTface{n}", "ffoctface{n}",
                "FFOCT{n}", "ffoct{n}"
            ],
        }
    },
    "hand": {
        "folder": "hand",
        "count": 10,
        "name_patterns": {
            "SSOCT": [
                "SSOCT{n}", "ssoct{n}",
                "SSOCThand{n}", "ssocthand{n}",
                "SSOCThandback{n}", "ssocthandback{n}"
            ],
            "CycleGAN": [
                "cycleganhand{n}", "CycleGANhand{n}",
                "cycleganhandback{n}", "CycleGANhandback{n}",
                "cyclegan{n}", "CycleGAN{n}"
            ],
            "FUSRGAN": [
                "fusrganhand{n}", "FUSRGANhand{n}",
                "fusrganhandback{n}", "FUSRGANhandback{n}",
                "fusrgan{n}", "FUSRGAN{n}"
            ],
            "OUR": [
                "ourhand{n}", "OURhand{n}",
                "ourhandback{n}", "OURhandback{n}",
                "our{n}", "OUR{n}"
            ],
            "FFOCT": [
                "FFOCThand{n}", "ffocthand{n}",
                "FFOCThandback{n}", "ffocthandback{n}",
                "FFOCT{n}", "ffoct{n}"
            ],
        }
    }
}


def find_image(region_dir, stems):
    """
    遞迴搜尋影像。
    支援以下兩種放法：
    1. rating_dataset/face/fusrganface1.jpg
    2. rating_dataset/face/case001/fusrganface1.jpg
    """
    for stem in stems:
        for root, _, files in os.walk(region_dir):
            for fn in files:
                name, ext = os.path.splitext(fn)
                if ext.lower() not in VALID_EXT:
                    continue
                if name == stem:
                    return os.path.join(root, fn)
    return None


def to_relative_path(abs_path):
    """
    Streamlit Cloud 不能使用 G:\\... 絕對路徑，
    因此 manifest 內存成 rating_dataset/... 相對路徑。
    """
    app_root = os.path.dirname(DATASET_ROOT)  # G:\app
    rel = os.path.relpath(abs_path, start=app_root)
    return rel.replace("\\", "/")


def main():
    random.seed(RANDOM_SEED)

    rows = []
    missing = []

    for region, cfg in REGIONS.items():
        region_dir = os.path.join(DATASET_ROOT, cfg["folder"])

        if not os.path.isdir(region_dir):
            print(f"[Warning] 找不到資料夾：{region_dir}")
            continue

        for case_number in range(1, cfg["count"] + 1):
            case_id = f"case{case_number:03d}"

            for method in METHODS:
                patterns = cfg["name_patterns"][method]
                stems = [p.format(n=case_number) for p in patterns]

                image_path = find_image(region_dir, stems)

                if image_path is None:
                    missing.append({
                        "region": region,
                        "case_number": case_number,
                        "case_id": case_id,
                        "method": method,
                        "expected_names": "; ".join(stems)
                    })
                    continue

                rows.append({
                    "region": region,
                    "case_id": case_id,
                    "case_number": case_number,
                    "method": method,
                    "image_path": to_relative_path(image_path)
                })

    if len(rows) == 0:
        print("沒有找到任何影像，請確認資料夾與檔名。")
        return

    # 隨機打亂全部影像
    random.shuffle(rows)

    # 產生匿名影像 ID
    for idx, row in enumerate(rows, start=1):
        row["image_id"] = f"Image_{idx:03d}"

    df = pd.DataFrame(rows)
    df = df[["image_id", "region", "case_id", "case_number", "method", "image_path"]]

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("==============================")
    print("manifest.csv 已建立完成")
    print("==============================")
    print(f"輸出位置：{OUTPUT_CSV}")
    print(f"總影像數：{len(df)}")
    print()
    print("各方法影像數：")
    print(df["method"].value_counts().reindex(METHODS, fill_value=0))
    print()
    print("各部位影像數：")
    print(df["region"].value_counts())
    print()

    expected_total = sum(cfg["count"] for cfg in REGIONS.values()) * len(METHODS)
    if len(df) == expected_total:
        print(f"數量正確：{len(df)} / {expected_total}")
    else:
        print(f"[Warning] 數量不完整：{len(df)} / {expected_total}")

    if len(missing) > 0:
        missing_csv = os.path.join(DATASET_ROOT, "missing_images.csv")
        pd.DataFrame(missing).to_csv(missing_csv, index=False, encoding="utf-8-sig")
        print()
        print(f"[Warning] 有缺少影像，已輸出：{missing_csv}")
        print(f"缺少數量：{len(missing)}")
    else:
        print("沒有缺少影像。")


if __name__ == "__main__":
    main()
