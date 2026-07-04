# -*- coding: utf-8 -*-
import os
import pandas as pd
import streamlit as st
from PIL import Image
from supabase import create_client


# =========================
# 檔案設定
# =========================
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
# 顯示名稱設定
# =========================
REGION_LABELS = {
    "face": "臉部皮膚",
    "hand": "手背皮膚",
    "handback": "手背皮膚"
}


def get_region_label(region):
    region = str(region).lower()
    return REGION_LABELS.get(region, str(region))


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
            padding-top: 3.4rem !important;
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
            margin-top: 0.2rem !important;
            margin-bottom: 0.45rem !important;
            line-height: 1.25 !important;
        }

        h2 {
            font-size: clamp(1.22rem, 1.7vw, 1.45rem) !important;
            margin-top: 0.25rem !important;
            margin-bottom: 0.20rem !important;
            line-height: 1.25 !important;
        }

        h3 {
            font-size: clamp(1.10rem, 1.4vw, 1.28rem) !important;
            margin-top: 0.20rem !important;
            margin-bottom: 0.20rem !important;
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
            margin-bottom: 0.18rem !important;
            font-size: clamp(0.92rem, 1.1vw, 1.04rem) !important;
            line-height: 1.45 !important;
        }

        .top-info {
            font-size: clamp(0.90rem, 1.1vw, 1.00rem);
            margin-bottom: 0.10rem;
            font-weight: 600;
            color: #111111 !important;
        }

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

        .intro-text {
            margin-bottom: 0.75rem !important;
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
            margin-bottom: 10px !important;
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
                padding-top: 3.0rem !important;
                padding-left: 0.7rem !important;
                padding-right: 0.7rem !important;
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


# =========================
# 第一頁：真實 FFOCT 參考影像
# =========================
def get_reference_ffoct_images(df, n_total=9):
    ref_df = df[df["method"].astype(str).str.upper() == "FFOCT"].copy()

    if len(ref_df) == 0:
        return ref_df

    ref_df = ref_df.sort_values(["region", "case_number", "case_id", "image_id"])

    face_df = ref_df[ref_df["region"].astype(str).str.lower() == "face"]
    hand_df = ref_df[ref_df["region"].astype(str).str.lower().isin(["hand", "handback"])]

    selected = []

    n_face = min(5, len(face_df))
    n_hand = min(4, len(hand_df))

    if n_face > 0:
        selected.append(face_df.head(n_face))
    if n_hand > 0:
        selected.append(hand_df.head(n_hand))

    if len(selected) > 0:
        selected_df = pd.concat(selected, ignore_index=True)
    else:
        selected_df = pd.DataFrame(columns=ref_df.columns)

    if len(selected_df) < n_total:
        used_ids = set(selected_df["image_id"].tolist())
        remain_df = ref_df[~ref_df["image_id"].isin(used_ids)]
        selected_df = pd.concat(
            [selected_df, remain_df.head(n_total - len(selected_df))],
            ignore_index=True
        )

    return selected_df.head(n_total)


def show_intro_page(df):
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

    ref_df = get_reference_ffoct_images(df, n_total=9)

    if len(ref_df) == 0:
        st.warning("manifest.csv 中找不到 method = FFOCT 的影像，無法顯示參考頁。")
        st.session_state.intro_done = True
        st.rerun()

    cols_per_row = 3

    for start_idx in range(0, len(ref_df), cols_per_row):
        cols = st.columns(cols_per_row)

        for col, (_, row) in zip(cols, ref_df.iloc[start_idx:start_idx + cols_per_row].iterrows()):
            with col:
                image_path = row["image_path"]
                region_label = get_region_label(row["region"])

                st.markdown(
                    f"<div class='reference-badge'>部位：{region_label}</div>",
                    unsafe_allow_html=True
                )

                if os.path.exists(image_path):
                    img = Image.open(image_path)
                    show_image_responsive(img)
                else:
                    st.error(f"找不到參考影像：{image_path}")

                st.markdown("<div style='height: 0.3rem;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 0.25rem;'></div>", unsafe_allow_html=True)

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
        show_intro_page(df)
        st.stop()

    if "expert_id" not in st.session_state:
        st.session_state.expert_id = "expert_1"

    expert_options = ["expert_1", "expert_2", "expert_3"]

    result_df = load_existing_result(st.session_state.expert_id)
    rated_ids = set(result_df["image_id"].tolist())

    total_images = len(df)
    rated_count = len(rated_ids)

    unrated_df = df[~df["image_id"].isin(rated_ids)]

    if len(unrated_df) == 0:
        st.success("此評分者已完成所有影像評分。")
        st.stop()

    current_row = unrated_df.iloc[0]
    image_id = current_row["image_id"]
    image_path = current_row["image_path"]
    region_label = get_region_label(current_row["region"])

    st.title("FFOCT 影像主觀評分系統")

    st.markdown(
        "請根據目前顯示的影像進行評分。每個項目皆為 **1 至 5 分**，其中 **1 分代表最差，5 分代表最好**。"
    )

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.15, 1.05, 3.4, 1.35])

    with top_col1:
        selected_expert = st.selectbox(
            "評分者",
            expert_options,
            index=expert_options.index(st.session_state.expert_id)
        )

    if selected_expert != st.session_state.expert_id:
        st.session_state.expert_id = selected_expert
        st.rerun()

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
            show_image_responsive(img, caption=image_id)

        else:
            st.error(f"找不到影像：{image_path}")
            st.stop()

    with right_col:
        st.markdown("### 評分項目")

        row1_col1, row1_col2 = st.columns(2)

        with row1_col1:
            overall_score = score_card(
                "overall",
                f"{image_id}_overall"
            )

        with row1_col2:
            layer_score = score_card(
                "layer",
                f"{image_id}_layer"
            )

        row2_col1, row2_col2 = st.columns(2)

        with row2_col1:
            nucleus_score = score_card(
                "nucleus",
                f"{image_id}_nucleus"
            )

        with row2_col2:
            artifact_score = score_card(
                "artifact",
                f"{image_id}_artifact"
            )

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