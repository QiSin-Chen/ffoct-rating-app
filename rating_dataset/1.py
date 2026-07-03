# -*- coding: utf-8 -*-
import pandas as pd

# =========================
# 需要修改的地方
# =========================
MANIFEST_CSV = r"G:\app\rating_dataset\manifest.csv"

OLD_ROOT = r"G:\snrgan\rating_dataset"
NEW_ROOT = r"rating_dataset"

df = pd.read_csv(MANIFEST_CSV)

if "image_path" not in df.columns:
    raise RuntimeError("manifest.csv 裡面找不到 image_path 欄位")

def fix_path(p):
    p = str(p)

    # 統一斜線，避免 Windows 反斜線問題
    p = p.replace("\\", "/")
    old_root = OLD_ROOT.replace("\\", "/")
    new_root = NEW_ROOT.replace("\\", "/")

    if p.startswith(old_root):
        p = p.replace(old_root, new_root, 1)

    return p

df["image_path"] = df["image_path"].apply(fix_path)

df.to_csv(MANIFEST_CSV, index=False, encoding="utf-8-sig")

print("完成：manifest.csv 的 image_path 已改成相對路徑")
print(df[["image_id", "image_path"]].head())