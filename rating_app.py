# -*- coding: utf-8 -*-
import os
import base64
import mimetypes
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client


# =========================
# 檔案設定
# =========================
MANIFEST_CSV = r"rating_dataset/manifest.csv"

# 第一頁範例影像資料夾
# 本機位置：G:\app\rating_dataset\example
# Streamlit Cloud 位置：rating_dataset/example
EXAMPLE_DIR = r"rating_dataset/example"

VALID_EXT = [".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]


# =========================
# Supabase 設定
# =========================
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )


# =========================
# 顯示名稱設定
# =========================
REGION_LABELS = {
    "face": "臉部皮膚",
    "hand": "手部皮膚",
    "handback": "手部皮膚"
}


def get_region_label(region):
    region = str(region).lower()
    return REGION_LABELS.get(region, str(region))


def get_example_region_label(filename_stem):
    name = filename_stem.lower()

    if name.startswith("hand"):
        return "手部皮膚"

    if name.startswith("face"):
        return "臉部皮膚"

    return "皮膚影像"


# =========================
# 評分項目與 1–5 分定義
# =========================
RATING_ITEMS = {
    "overall": {
        "title": "1. FFOCT-like appearance",
        "subtitle": "整體是否像真實 FFOCT 影像",
        "options": {
            1: "1：完全不像 FFOCT，仍呈現明顯 SSOCT 或雜訊外觀。",
            2: "2：僅少部分區域具有 FFOCT-like 特徵。",
            3: "3：中等程度接近 FFOCT，但仍可見明顯差異。",
            4: "4：多數區域接近 FFOCT 外觀。",
            5: "5：整體高度接近真實 FFOCT 影像。"
        }
    },
    "layer": {
        "title": "2. Skin layer visibility",
        "subtitle": "皮膚層狀結構是否清楚",
        "options": {
            1: "1：幾乎無法辨識皮膚層。",
            2: "2：僅可粗略看到表面或單一層次。",
            3: "3：可辨識部分皮膚層，但邊界不穩定或不連續。",
            4: "4：多數皮膚層可清楚辨識，僅局部模糊。",
            5: "5：皮膚層結構清楚、連續，具有良好判讀性。"
        }
    },
    "nucleus": {
        "title": "3. Nuclei-like microstructure visibility",
        "subtitle": "細胞核樣微結構是否可見",
        "options": {
            1: "1：完全無可辨識細胞核樣結構。",
            2: "2：僅有少數不明確亮點或疑似結構。",
            3: "3：可見部分細胞核樣特徵，但數量或邊界不穩定。",
            4: "4：多數區域可見合理細胞核樣微結構。",
            5: "5：細胞核樣結構清楚、分布自然，接近真實 FFOCT 表現。"
        }
    },
    "artifact": {
        "title": "4. Artifact-free score",
        "subtitle": "影像是否無明顯偽影",
        "options": {
            1: "1：偽影嚴重，明顯影響判讀。",
            2: "2：有多處偽影，影響部分結構判斷。",
            3: "3：有中等程度偽影，但仍可部分判讀。",
            4: "4：僅有少量輕微偽影，不明顯影響判讀。",
            5: "5：幾乎無明顯偽影，影像穩定且自然。"
        }
    }
}


# =========================
# 載入 manifest
# =========================
@st.cache_data
def load_manifest():
    if not os.path.exists(MANIFEST_CSV):
        raise FileNotFoundError(f"找不到 manifest.csv：{MANIFEST_CSV}")

    df = pd.read_csv(MANIFEST_CSV)

    required_cols = [
        "image_id",
        "region",
        "case_id",
        "case_number",
        "method",
        "image_path"
    ]

    for col in required_cols:
        if col not in df.columns:
            raise RuntimeError(f"manifest.csv 缺少欄位：{col}")

    return df


def get_empty_result_df():
    return pd.DataFrame(columns=[
        "expert_id",
        "image_id",
        "region",
        "case_id",
        "case_number",
        "method",
        "overall_score",
        "layer_score",
        "nucleus_score",
        "artifact_score"
    ])


def load_existing_result(expert_id):
    if expert_id.strip() == "":
        return get_empty_result_df()

    supabase = get_supabase_client()

    try:
        response = (
            supabase.table("ratings")
            .select(
                "expert_id,image_id,region,case_id,case_number,method,"
                "overall_score,layer_score,nucleus_score,artifact_score"
            )
            .eq("expert_id", expert_id)
            .execute()
        )
    except Exception as e:
        st.error("讀取 Supabase ratings 資料表失敗。")
        st.exception(e)
        st.stop()

    data = response.data or []

    if len(data) == 0:
        return get_empty_result_df()

    df = pd.DataFrame(data)

    keep_cols = [
        "expert_id",
        "image_id",
        "region",
        "case_id",
        "case_number",
        "method",
        "overall_score",
        "layer_score",
        "nucleus_score",
        "artifact_score"
    ]

    for col in keep_cols:
        if col not in df.columns:
            df[col] = None

    return df[keep_cols]


def save_rating(row_data):
    supabase = get_supabase_client()

    payload = {
        "expert_id": str(row_data["expert_id"]),
        "image_id": str(row_data["image_id"]),
        "region": str(row_data["region"]),
        "case_id": str(row_data["case_id"]),
        "case_number": int(row_data["case_number"]),
        "method": str(row_data["method"]),
        "overall_score": int(row_data["overall_score"]),
        "layer_score": int(row_data["layer_score"]),
        "nucleus_score": int(row_data["nucleus_score"]),
        "artifact_score": int(row_data["artifact_score"])
    }

    try:
        supabase.table("ratings").upsert(
            payload,
            on_conflict="expert_id,image_id"
        ).execute()
    except Exception as e:
        st.error("寫入 Supabase ratings 資料表失敗。")
        st.exception(e)
        st.stop()


# =========================
# CSS 版面設定
# =========================
def inject_css():
    st.markdown(
        """
        <style>
        html, body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"] {
            background-color: #ffffff !important;
            color: #111111 !important;
        }

        [data-testid="stHeader"] {
            background: #ffffff !important;
        }

        .block-container {
            padding-top: 2.6rem !important;
            padding-bottom: 0.8rem !important;
            padding-left: 1.2rem !important;
            padding-right: 1.2rem !important;
            max-width: 100% !important;
            background-color: #ffffff !important;
            color: #111111 !important;
        }

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        h1, h2, h3, h4, h5, h6,
        p, label, span,
        [data-testid="stMarkdownContainer"],
        [data-testid="stText"],
        [data-testid="stCaptionContainer"] {
            color: #111111 !important;
        }

        h1 {
            font-size: clamp(1.55rem, 2vw, 1.95rem) !important;
            margin-top: 0.1rem !important;
            margin-bottom: 0.35rem !important;
            line-height: 1.25 !important;
        }

        h2 {
            font-size: clamp(1.18rem, 1.6vw, 1.42rem) !important;
            margin-top: 0.18rem !important;
            margin-bottom: 0.16rem !important;
            line-height: 1.25 !important;
        }

        h3 {
            font-size: clamp(1.08rem, 1.35vw, 1.25rem) !important;
            margin-top: 0.14rem !important;
            margin-bottom: 0.16rem !important;
            line-height: 1.25 !important;
        }

        h4 {
            font-size: clamp(1.02rem, 1.25vw, 1.20rem) !important;
            margin-top: 0.10rem !important;
            margin-bottom: 0.18rem !important;
            line-height: 1.25 !important;
        }

        p {
            margin-top: 0rem !important;
            margin-bottom: 0.16rem !important;
            font-size: clamp(0.92rem, 1.1vw, 1.04rem) !important;
            line-height: 1.40 !important;
        }

        .top-info {
            font-size: clamp(0.90rem, 1.1vw, 1.00rem);
            margin-bottom: 0.10rem;
            font-weight: 600;
            color: #111111 !important;
        }

        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] span,
        div[data-baseweb="input"] > div,
        input {
            background-color: #ffffff !important;
            color: #111111 !important;
            border-color: #cccccc !important;
        }

        div[data-baseweb="popover"] {
            background-color: #ffffff !important;
            color: #111111 !important;
        }

        ul[role="listbox"],
        li[role="option"] {
            background-color: #ffffff !important;
            color: #111111 !important;
        }

        li[role="option"]:hover {
            background-color: #f2f2f2 !important;
            color: #111111 !important;
        }

        .intro-text {
            margin-bottom: 0.55rem !important;
            line-height: 1.42 !important;
        }

        .reference-badge,
        .region-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 999px;
            background-color: #eeeeee;
            border: 1px solid #cccccc;
            font-size: clamp(0.85rem, 1vw, 0.98rem);
            font-weight: 600;
            color: #111111 !important;
            margin-top: 0rem !important;
            margin-bottom: 6px !important;
        }

        .example-grid {
            display: grid;
            grid-template-columns: repeat(3, max-content);
            column-gap: 28px;
            row-gap: 12px;
            align-items: start;
            justify-content: start;
            margin-top: 0.45rem;
        }

        .example-tile {
            display: block;
            margin: 0;
            padding: 0;
        }

        .example-original-img {
            display: block;
            width: auto;
            height: auto;
            max-width: 100%;
            border-radius: 8px;
            background-color: transparent;
            margin: 0;
            padding: 0;
        }

        .score-subtitle {
            font-weight: 700;
            margin-top: 0rem;
            margin-bottom: 0.55rem;
            font-size: clamp(1.00rem, 1.10vw, 1.12rem);
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #f7f7f7 !important;
            border: 1px solid #d8d8d8 !important;
            border-radius: 8px !important;
            padding-top: 0.2rem !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] * {
            color: #111111 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] div[role="radiogroup"] {
            margin-top: 0rem !important;
            margin-bottom: 0rem !important;
            background-color: #f7f7f7 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] {
            display: flex !important;
            align-items: center !important;
            min-height: 32px !important;
            margin-top: 2px !important;
            margin-bottom: 2px !important;
            padding: 2px 4px !important;
            cursor: pointer !important;
            color: #111111 !important;
            background-color: #f7f7f7 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] p,
        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] span {
            font-size: clamp(0.96rem, 1.08vw, 1.08rem) !important;
            color: #111111 !important;
            line-height: 1.35 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] > div:first-child {
            transform: scale(1.10);
            margin-right: 0.65rem !important;
            background-color: #ffffff !important;
            border: 1.1px solid #111111 !important;
            box-shadow: none !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] svg,
        [data-testid="stVerticalBlockBorderWrapper"] label[data-baseweb="radio"] path {
            color: #111111 !important;
            fill: #111111 !important;
            stroke: #111111 !important;
        }

        .stButton > button {
            width: 100%;
            height: 3.0rem;
            font-size: clamp(0.95rem, 1.1vw, 1.08rem);
            font-weight: 700;
            border-radius: 8px;
            background-color: #ffffff !important;
            color: #111111 !important;
            border: 1px solid #cccccc !important;
        }

        .stButton > button:hover {
            background-color: #f2f2f2 !important;
            color: #111111 !important;
            border: 1px solid #999999 !important;
        }

        .stButton > button:active,
        .stButton > button:focus {
            background-color: #eaeaea !important;
            color: #111111 !important;
            border: 1px solid #777777 !important;
        }

        [data-testid="stCaptionContainer"] {
            font-size: clamp(0.78rem, 0.95vw, 0.90rem) !important;
            margin-top: 0.10rem !important;
            margin-bottom: 0.35rem !important;
            color: #6b7280 !important;
        }

        [data-testid="stImage"] img {
            border-radius: 8px !important;
        }

        div[data-testid="stVerticalBlock"] {
            gap: 0.28rem !important;
        }

        @media (max-width: 900px) {
            .block-container {
                padding-top: 2.8rem !important;
                padding-left: 0.7rem !important;
                padding-right: 0.7rem !important;
            }

            .example-grid {
                grid-template-columns: repeat(2, max-content);
                column-gap: 18px;
                row-gap: 12px;
            }
        }

        @media (max-width: 560px) {
            .example-grid {
                grid-template-columns: repeat(1, max-content);
            }
        }
        </style>
        """,
        unsafe_allow_html=True
    )


# =========================
# 圖片顯示工具
# =========================
def show_image_responsive(img, caption=None):
    try:
        st.image(img, caption=caption, use_container_width=True)
    except TypeError:
        st.image(img, caption=caption, use_column_width=True)


def show_image_original(img, caption=None):
    """
    正式評分頁影像專用：
    用原圖尺寸呈現，不強制放大。
    """
    st.image(img, caption=caption)


def find_image_by_stem(folder, stem):
    for ext in VALID_EXT:
        candidate = os.path.join(folder, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def get_mime_type(image_path):
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        return "image/png"
    return mime_type


def show_example_image_original(image_path):
    """
    第一頁 example 專用：
    保留原圖尺寸，不主動放大。
    """
    img_b64 = image_to_base64(image_path)
    mime_type = get_mime_type(image_path)

    st.markdown(
        f"""
        <img class="example-original-img"
             src="data:{mime_type};base64,{img_b64}">
        """,
        unsafe_allow_html=True
    )


# =========================
# 第一頁：固定 example 範例影像
# =========================
def get_example_images():
    ordered_stems = [
        "hand1", "hand2", "hand3", "hand4", "hand5",
        "face1", "face2", "face3", "face4"
    ]

    rows = []

    for stem in ordered_stems:
        path = find_image_by_stem(EXAMPLE_DIR, stem)

        rows.append({
            "stem": stem,
            "image_path": path,
            "region_label": get_example_region_label(stem)
        })

    return rows


def show_intro_page():
    st.title("FFOCT 影像主觀評分系統")

    st.markdown(
        """
### 評分前參考：真實 FFOCT 影像範例

<div class="intro-text">
以下影像為真實 FFOCT 影像，請先觀察其整體外觀、皮膚層狀結構、細胞核樣微結構與影像自然程度。<br>
看完後請按下方按鈕開始正式評分。
</div>
        """,
        unsafe_allow_html=True
    )

    example_rows = get_example_images()

    if not os.path.isdir(EXAMPLE_DIR):
        st.warning(f"找不到範例資料夾：{EXAMPLE_DIR}")
        st.info("請建立資料夾 rating_dataset/example，並放入 hand1-hand5、face1-face4 的圖片。")

    html_parts = ["<div class='example-grid'>"]

    for row in example_rows:
        html_parts.append("<div class='example-tile'>")
        html_parts.append(
            f"<div class='reference-badge'>部位：{row['region_label']}</div>"
        )

        image_path = row["image_path"]

        if image_path is not None and os.path.exists(image_path):
            img_b64 = image_to_base64(image_path)
            mime_type = get_mime_type(image_path)
            html_parts.append(
                f"<img class='example-original-img' src='data:{mime_type};base64,{img_b64}'>"
            )
        else:
            html_parts.append(
                f"<div style='color:#b00020;font-weight:600;'>缺少範例影像：{row['stem']}</div>"
            )

        html_parts.append("</div>")

    html_parts.append("</div>")

    st.markdown("\n".join(html_parts), unsafe_allow_html=True)

    st.markdown("<div style='height: 0.55rem;'></div>", unsafe_allow_html=True)

    col_left, col_mid, col_right = st.columns([2, 1.2, 2])

    with col_mid:
        if st.button("我已看完參考影像，開始評分"):
            st.session_state.intro_done = True
            st.rerun()


# =========================
# 評分卡片
# =========================
def score_card(item_key, radio_key):
    item = RATING_ITEMS[item_key]

    st.markdown(f"#### {item['title']}")

    with st.container(border=True):
        st.markdown(
            f"<div class='score-subtitle'>{item['subtitle']}</div>",
            unsafe_allow_html=True
        )

        score = st.radio(
            label=item["title"],
            options=[1, 2, 3, 4, 5],
            format_func=lambda x: item["options"][x],
            index=None,
            key=radio_key,
            label_visibility="collapsed"
        )

    return score


# =========================
# 主程式
# =========================
def main():
    st.set_page_config(
        page_title="FFOCT Subjective Rating",
        layout="wide"
    )

    inject_css()

    df = load_manifest()

    if "intro_done" not in st.session_state:
        st.session_state.intro_done = False

    if not st.session_state.intro_done:
        show_intro_page()
        st.stop()

    if "rater_name" not in st.session_state:
        st.session_state.rater_name = ""

    st.title("FFOCT 影像主觀評分系統")

    st.markdown(
        "請根據目前顯示的影像進行評分。每個項目皆為 **1 至 5 分**，其中 **1 分代表最差，5 分代表最好**。"
    )

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.20, 1.05, 3.35, 1.35])

    with top_col1:
        rater_name = st.text_input(
            "評分者姓名",
            value=st.session_state.rater_name,
            placeholder="請輸入姓名",
            key="rater_name_input"
        ).strip()

    st.session_state.rater_name = rater_name

    if rater_name == "":
        result_df = get_empty_result_df()
    else:
        result_df = load_existing_result(rater_name)

    rated_ids = set(result_df["image_id"].tolist())
    total_images = len(df)
    rated_count = len(rated_ids)
    progress = rated_count / total_images if total_images > 0 else 0

    unrated_df = df[~df["image_id"].isin(rated_ids)]

    if len(unrated_df) == 0 and rater_name != "":
        st.success("此評分者已完成所有影像評分。")
        st.stop()

    if len(unrated_df) == 0:
        current_row = df.iloc[0]
    else:
        current_row = unrated_df.iloc[0]

    image_id = current_row["image_id"]
    image_path = current_row["image_path"]
    region_label = get_region_label(current_row["region"])

    with top_col2:
        st.markdown("<div class='top-info'>完成進度</div>", unsafe_allow_html=True)
        st.write(f"{rated_count} / {total_images}")
        st.progress(progress)

    with top_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader(image_id)

    with top_col4:
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.button("儲存並前往下一張")

    left_col, right_col = st.columns([1.00, 3.35])

    with left_col:
        if os.path.exists(image_path):
            img = Image.open(image_path)

            st.markdown(
                f"<div class='region-badge'>部位：{region_label}</div>",
                unsafe_allow_html=True
            )
            st.caption(f"原始尺寸：{img.width} × {img.height}")
            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)

            # 正式評分頁：原圖大小呈現，不強制放大
            show_image_original(img, caption=image_id)

        else:
            st.error(f"找不到影像：{image_path}")
            st.stop()

    safe_key_name = rater_name if rater_name != "" else "blank"

    with right_col:
        st.markdown("### 評分項目")

        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            overall_score = score_card(
                "overall",
                f"{safe_key_name}_{image_id}_overall"
            )

        with row1_col2:
            layer_score = score_card(
                "layer",
                f"{safe_key_name}_{image_id}_layer"
            )

        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            nucleus_score = score_card(
                "nucleus",
                f"{safe_key_name}_{image_id}_nucleus"
            )

        with row2_col2:
            artifact_score = score_card(
                "artifact",
                f"{safe_key_name}_{image_id}_artifact"
            )

    if submit:
        if rater_name == "":
            st.warning("請先在左上角輸入評分者姓名。")
            st.stop()

        if (
            overall_score is None or
            layer_score is None or
            nucleus_score is None or
            artifact_score is None
        ):
            st.warning("請完成四個評分項目後再儲存。")
            st.stop()

        row_data = {
            "expert_id": rater_name,
            "image_id": current_row["image_id"],
            "region": current_row["region"],
            "case_id": current_row["case_id"],
            "case_number": current_row["case_number"],
            "method": current_row["method"],
            "overall_score": overall_score,
            "layer_score": layer_score,
            "nucleus_score": nucleus_score,
            "artifact_score": artifact_score
        }

        save_rating(row_data)

        st.success("已儲存，請繼續下一張。")
        st.rerun()


if __name__ == "__main__":
    main()