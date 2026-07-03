# -*- coding: utf-8 -*-
import os
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client


# =========================
# 檔案設定
# =========================
# 遠端部署版一定要用相對路徑，不能用 G:\...
MANIFEST_CSV = r"rating_dataset/manifest.csv"


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
# 評分定義文字
# =========================
SCORE_DEFINITIONS = {
    "overall": """
<b>FFOCT-like appearance<br>整體是否像真實 FFOCT 影像</b><br>
1：完全不像 FFOCT，仍呈現明顯 SSOCT 或雜訊外觀。<br>
2：僅少部分區域具有 FFOCT-like 特徵。<br>
3：中等程度接近 FFOCT，但仍可見明顯差異。<br>
4：多數區域接近 FFOCT 外觀。<br>
5：整體高度接近真實 FFOCT 影像。
""",

    "layer": """
<b>Skin layer visibility<br>皮膚層狀結構是否清楚</b><br>
1：幾乎無法辨識皮膚層。<br>
2：僅可粗略看到表面或單一層次。<br>
3：可辨識部分皮膚層，但邊界不穩定或不連續。<br>
4：多數皮膚層可清楚辨識，僅局部模糊。<br>
5：皮膚層結構清楚、連續，具有良好判讀性。
""",

    "nucleus": """
<b>Nuclei-like microstructure visibility<br>細胞核樣微結構是否可見</b><br>
1：完全無可辨識細胞核樣結構。<br>
2：僅有少數不明確亮點或疑似結構。<br>
3：可見部分細胞核樣特徵，但數量或邊界不穩定。<br>
4：多數區域可見合理細胞核樣微結構。<br>
5：細胞核樣結構清楚、分布自然，接近真實 FFOCT 表現。
""",

    "artifact": """
<b>Artifact-free score<br>影像是否無明顯偽影</b><br>
1：偽影嚴重，明顯影響判讀。<br>
2：有多處偽影，影響部分結構判斷。<br>
3：有中等程度偽影，但仍可部分判讀。<br>
4：僅有少量輕微偽影，不明顯影響判讀。<br>
5：幾乎無明顯偽影，影像穩定且自然。
"""
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
    """
    從 Supabase 讀取指定 expert 已評過的資料。
    用來判斷哪些 image_id 要跳過。
    """
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


def save_rating(row_data, expert_id):
    """
    將評分結果寫入 Supabase。
    使用 upsert，確保同一位 expert 對同一張 image_id 只保留一筆資料。
    """
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
        /* =========================================================
           Force light theme
           避免使用者系統 / 瀏覽器 / Streamlit dark mode 影響顯示
        ========================================================= */

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

        /* 整體版面 */
        .block-container {
            padding-top: 2.4rem !important;
            padding-bottom: 0.4rem !important;
            padding-left: 1.1rem !important;
            padding-right: 1.1rem !important;
            max-width: 100% !important;
            background-color: #ffffff !important;
            color: #111111 !important;
        }

        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* 全域文字固定深色 */
        h1, h2, h3, h4, h5, h6,
        p, label, span,
        [data-testid="stMarkdownContainer"],
        [data-testid="stText"],
        [data-testid="stCaptionContainer"] {
            color: #111111 !important;
        }

        h1 {
            font-size: 1.80rem !important;
            margin-top: 0rem !important;
            margin-bottom: 0.22rem !important;
        }

        h2 {
            font-size: 1.36rem !important;
            margin-top: 0.10rem !important;
            margin-bottom: 0.10rem !important;
        }

        h3 {
            font-size: 1.22rem !important;
            margin-top: 0.10rem !important;
            margin-bottom: 0.16rem !important;
        }

        h4 {
            font-size: 1.22rem !important;
            margin-top: 0.06rem !important;
            margin-bottom: 0.14rem !important;
        }

        p {
            margin-top: 0rem !important;
            margin-bottom: 0.12rem !important;
            font-size: 0.98rem !important;
        }

        .top-info {
            font-size: 1.00rem;
            margin-bottom: 0.15rem;
            font-weight: 600;
            color: #111111 !important;
        }

        /* =========================================================
           Selectbox：強制白底黑字
        ========================================================= */

        div[data-baseweb="select"] > div,
        div[data-baseweb="select"] div,
        div[data-baseweb="select"] span {
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

        /* =========================================================
           評分說明框：固定白底黑字
        ========================================================= */

        .score-box {
            background-color: #f7f7f7 !important;
            color: #111111 !important;
            padding: 12px 15px;
            border-radius: 8px;
            border: 1px solid #d8d8d8;
            font-size: 17px;
            line-height: 1.48;
            height: 210px;
            overflow: hidden;
            margin-bottom: 8px;
        }

        .score-box,
        .score-box b,
        .score-box span,
        .score-box div,
        .score-box p,
        .score-box * {
            color: #111111 !important;
            background-color: transparent !important;
        }

        .score-box {
            background-color: #f7f7f7 !important;
        }

        /* =========================================================
           Radio：強制白底、黑字、灰框，避免 dark mode 變黑圈
        ========================================================= */

        /* radio 整組往下，避免卡到題目框 */
div[role="radiogroup"] {
    margin-top: 0.45rem !important;
    margin-bottom: 0.35rem !important;
    color: #111111 !important;
    background-color: #ffffff !important;
}

/* radio 每個選項的點擊範圍變大 */
label[data-baseweb="radio"] {
    margin-right: 1.05rem !important;
    padding: 8px 4px !important;
    font-size: 1.28rem !important;
    cursor: pointer !important;
    color: #111111 !important;
    background-color: #ffffff !important;
}

/* radio 數字固定黑色 */
label[data-baseweb="radio"] p,
label[data-baseweb="radio"] span {
    font-size: 1.28rem !important;
    margin-left: 0.20rem !important;
    color: #111111 !important;
    background-color: #ffffff !important;
}

/* radio 外圈：強制黑框 */
label[data-baseweb="radio"] > div:first-child {
    transform: scale(1.55);
    margin-right: 0.45rem !important;
    background-color: #ffffff !important;
    border: 1.5px solid #111111 !important;
    box-shadow: 0 0 0 2px #111111 inset !important;
}

/* radio 內部圓點：選到時顯示藍色 */
label[data-baseweb="radio"] > div:first-child div {
    background-color: #1f77b4 !important;
}

/* radio svg / path 顏色 */
label[data-baseweb="radio"] svg,
label[data-baseweb="radio"] path {
    color: #1f77b4 !important;
    fill: #1f77b4 !important;
    stroke: #1f77b4 !important;
}

        label[data-baseweb="radio"] {
            margin-right: 1.05rem !important;
            padding: 8px 4px !important;
            font-size: 1.28rem !important;
            cursor: pointer !important;
            color: #111111 !important;
            background-color: #ffffff !important;
        }

        label[data-baseweb="radio"] p,
        label[data-baseweb="radio"] span {
            font-size: 1.28rem !important;
            margin-left: 0.20rem !important;
            color: #111111 !important;
            background-color: #ffffff !important;
        }

        /* radio 圓圈本體放大，並固定未選取樣式 */
        label[data-baseweb="radio"] > div:first-child {
            transform: scale(1.55);
            margin-right: 0.45rem !important;
            background-color: #ffffff !important;
            border-color: #777777 !important;
        }

        /* radio 內部 SVG / path 顏色保留可見 */
        label[data-baseweb="radio"] svg {
            color: #1f77b4 !important;
            fill: #1f77b4 !important;
        }

        /* =========================================================
           Button：強制白底黑字
        ========================================================= */

        .stButton > button {
            width: 100%;
            height: 3.0rem;
            font-size: 1.08rem;
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
            font-size: 0.85rem !important;
            margin-bottom: 0.35rem !important;
            color: #6b7280 !important;
        }

        hr {
            margin-top: 0.25rem !important;
            margin-bottom: 0.25rem !important;
        }

        /* 壓縮四個評分卡之間的縱向距離，但保留 radio 空間 */
        div[data-testid="stVerticalBlock"] {
            gap: 0.28rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def show_score_definition(html_text):
    st.markdown(
        f"<div class='score-box'>{html_text.strip()}</div>",
        unsafe_allow_html=True
    )


def score_card(title, definition_key, radio_key):
    st.markdown(f"#### {title}")
    show_score_definition(SCORE_DEFINITIONS[definition_key])

    # 讓 1–5 分圓圈往下，不要卡到上方定義框
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    score = st.radio(
        title,
        [1, 2, 3, 4, 5],
        horizontal=True,
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

    # =========================
    # Session state：評分者
    # =========================
    if "expert_id" not in st.session_state:
        st.session_state.expert_id = "expert_1"

    expert_options = ["expert_1", "expert_2", "expert_3"]

    # =========================
    # 讀取目前 expert 的進度
    # =========================
    result_df = load_existing_result(st.session_state.expert_id)
    rated_ids = set(result_df["image_id"].tolist())

    total_images = len(df)
    rated_count = len(rated_ids)
    progress = rated_count / total_images if total_images > 0 else 0

    unrated_df = df[~df["image_id"].isin(rated_ids)]

    if len(unrated_df) == 0:
        st.success("此評分者已完成所有影像評分。")
        st.stop()

    current_row = unrated_df.iloc[0]
    image_id = current_row["image_id"]
    image_path = current_row["image_path"]

    # =========================
    # 上方：標題 + 評分者設定 + 右上儲存按鈕
    # =========================
    st.title("FFOCT 影像主觀評分系統")

    st.markdown(
        "請根據目前顯示的影像進行評分。每個項目皆為 **1 至 5 分**，其中 **1 分代表最差，5 分代表最好**。"
    )

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.2, 1.1, 3.8, 1.25])

    with top_col1:
        selected_expert = st.selectbox(
            "評分者",
            expert_options,
            index=expert_options.index(st.session_state.expert_id)
        )

    if selected_expert != st.session_state.expert_id:
        st.session_state.expert_id = selected_expert
        st.rerun()

    # 重新讀取切換後的 expert 進度
    result_df = load_existing_result(st.session_state.expert_id)
    rated_ids = set(result_df["image_id"].tolist())
    rated_count = len(rated_ids)
    progress = rated_count / total_images if total_images > 0 else 0

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

    # =========================
    # 主畫面：左邊影像，右邊 2×2 評分項目
    # =========================
    left_col, right_col = st.columns([1.00, 3.10])

    with left_col:
        if os.path.exists(image_path):
            img = Image.open(image_path)

            st.caption(f"原始尺寸：{img.width} × {img.height}")

            # 讓圖片往下一點，避免卡到原始尺寸文字
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            st.image(img, caption=image_id, width=420)

        else:
            st.error(f"找不到影像：{image_path}")
            st.stop()

    with right_col:
        st.markdown("### 評分項目")

        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            overall_score = score_card(
                "1. FFOCT-like appearance",
                "overall",
                f"{image_id}_overall"
            )

        with row1_col2:
            layer_score = score_card(
                "2. Skin layer visibility",
                "layer",
                f"{image_id}_layer"
            )

        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            nucleus_score = score_card(
                "3. Nuclei-like visibility",
                "nucleus",
                f"{image_id}_nucleus"
            )

        with row2_col2:
            artifact_score = score_card(
                "4. Artifact-free score",
                "artifact",
                f"{image_id}_artifact"
            )

    # =========================
    # 儲存邏輯
    # =========================
    if submit:
        if (
            overall_score is None or
            layer_score is None or
            nucleus_score is None or
            artifact_score is None
        ):
            st.warning("請完成四個評分項目後再儲存。")
            st.stop()

        row_data = {
            "expert_id": st.session_state.expert_id,
            "image_id": current_row["image_id"],

            # 後台答案，專家畫面不顯示
            "region": current_row["region"],
            "case_id": current_row["case_id"],
            "case_number": current_row["case_number"],
            "method": current_row["method"],

            "overall_score": overall_score,
            "layer_score": layer_score,
            "nucleus_score": nucleus_score,
            "artifact_score": artifact_score
        }

        save_rating(row_data, st.session_state.expert_id)

        st.success("已儲存，請繼續下一張。")
        st.rerun()


if __name__ == "__main__":
    main()