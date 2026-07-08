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


# =========================
# Example 參考影像設定
# =========================
# 目前支援 G:\app\rating_dataset\example 內這 15 張：
# face1-face3、hand1-hand3、SSOCT1-SSOCT3、偽影1-偽影3、facelayer1、handlayer1-handlayer2
EXAMPLE_GROUPS = [
    {
        "group_title": "真實 FFOCT：臉部皮膚範例",
        "group_note": "觀察臉部皮膚在真實 FFOCT 中的整體外觀、層狀結構與微結構分布。",
        "items": [
            {"stem": "face1", "badge": "部位：臉部皮膚"},
            {"stem": "face2", "badge": "部位：臉部皮膚"},
            {"stem": "face3", "badge": "部位：臉部皮膚"},
        ],
    },
    {
        "group_title": "真實 FFOCT：手部皮膚範例",
        "group_note": "觀察手部皮膚在真實 FFOCT 中的表面形態、皮膚厚度與影像紋理。",
        "items": [
            {"stem": "hand1", "badge": "部位：手部皮膚"},
            {"stem": "hand2", "badge": "部位：手部皮膚"},
            {"stem": "hand3", "badge": "部位：手部皮膚"},
        ],
    },
    {
        "group_title": "SSOCT 外觀參考",
        "group_note": "SSOCT 影像通常較接近深層掃描外觀，與真實 FFOCT 的高解析表面微結構不同。",
        "items": [
            {"stem": "SSOCT1", "badge": "類型：SSOCT"},
            {"stem": "SSOCT2", "badge": "類型：SSOCT"},
            {"stem": "SSOCT3", "badge": "類型：SSOCT"},
        ],
    },
    {
        "group_title": "偽影與異常生成參考",
        "group_note": "評分時請注意明顯條紋、斷裂、非自然亮暗變化、錯誤紋理或亂生成結構。",
        "items": [
            {"stem": "偽影1", "badge": "類型：偽影範例"},
            {"stem": "偽影2", "badge": "類型：偽影範例"},
            {"stem": "偽影3", "badge": "類型：偽影範例"},
        ],
    },
    {
        "group_title": "FFOCT 皮膚層結構參考",
        "group_note": "觀察角質層、表皮層與真皮層的層次分布，並注意表皮層與真皮層邊界是否清楚、連續且位置合理。",
        "items": [
            {"stem": "facelayer1", "badge": "層次：臉部皮膚"},
            {"stem": "handlayer1", "badge": "層次：手部皮膚"},
            {"stem": "handlayer2", "badge": "層次：手部皮膚"},
        ],
    },
]


# =========================
# 評分項目與 1–5 分定義
# =========================
RATING_ITEMS = {
    "overall": {
        "title": "1. FFOCT-like appearance",
        "subtitle": "整體是否像真實 FFOCT 影像",
        "options": {
            1: "1：完全不像 FFOCT。",
            2: "2：僅少部分區域具有 FFOCT-like 特徵。",
            3: "3：中等程度接近 FFOCT，但仍可見明顯差異。",
            4: "4：多數區域接近 FFOCT 外觀。",
            5: "5：整體高度接近真實 FFOCT 影像。"
        }
    },
    "layer": {
        "title": "2. Epidermis–dermis boundary visibility",
        "subtitle": "表皮層與真皮層邊界是否清楚、連續且位置合理",
        "options": {
            1: "1：幾乎無法辨識表皮層與真皮層之間的邊界位置。",
            2: "2：僅可粗略看到疑似邊界，但位置不明確或判讀困難。",
            3: "3：可辨識部分表皮–真皮邊界，但邊界不連續、模糊或位置不穩定。",
            4: "4：大多數區域可清楚辨識表皮–真皮邊界，僅局部模糊或中斷。",
            5: "5：表皮–真皮邊界清楚、連續，位置合理，具有良好判讀性。"
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

        .example-section-title {
            font-size: clamp(1.02rem, 1.12vw, 1.14rem);
            font-weight: 700;
            margin-top: 0.85rem;
            margin-bottom: 0.18rem;
            color: #111111 !important;
            line-height: 1.30 !important;
        }

        .example-section-note {
            font-size: clamp(0.84rem, 0.95vw, 0.95rem);
            color: #555555 !important;
            margin-top: 0rem;
            margin-bottom: 0.55rem;
            line-height: 1.50 !important;
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

        [data-testid="stImage"] img {
            border-radius: 8px !important;
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
def show_image_original(img, caption=None, scale=1.0):
    """
    顯示影像。
    scale=1.0：原圖大小。
    scale=1.5：放大為原圖的 1.5 倍，用於正式評分頁。
    """
    if scale is None or scale == 1.0:
        st.image(img, caption=caption)
    else:
        display_width = max(1, int(round(img.width * scale)))
        st.image(img, caption=caption, width=display_width)


def find_image_by_stem(folder, stem):
    for ext in VALID_EXT:
        candidate = os.path.join(folder, stem + ext)
        if os.path.exists(candidate):
            return candidate
    return None


# =========================
# 第一頁：固定 example 範例影像
# =========================
def get_example_groups():
    groups = []

    for group in EXAMPLE_GROUPS:
        items = []
        for item in group["items"]:
            stem = item["stem"]
            path = find_image_by_stem(EXAMPLE_DIR, stem)
            items.append({
                "stem": stem,
                "image_path": path,
                "badge": item["badge"]
            })

        groups.append({
            "group_title": group["group_title"],
            "group_note": group["group_note"],
            "items": items
        })

    return groups


def render_example_items(items, cols_per_row=3, image_scale=1.0):
    """
    第一頁範例影像顯示。
    image_scale=1.5：用於臉部、手部、SSOCT、偽影範例。
    image_scale=1.0：用於最下面皮膚層結構參考，維持原圖大小。
    """
    for start_idx in range(0, len(items), cols_per_row):
        cols = st.columns(cols_per_row)

        for col, item in zip(cols, items[start_idx:start_idx + cols_per_row]):
            with col:
                st.markdown(
                    f"<div class='reference-badge'>{item['badge']}</div>",
                    unsafe_allow_html=True
                )

                # 標籤與影像之間多留一點距離，避免放大後卡到文字
                st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

                image_path = item["image_path"]

                if image_path is not None and os.path.exists(image_path):
                    img = Image.open(image_path)
                    show_image_original(img, scale=image_scale)
                else:
                    st.warning(f"缺少範例影像：{item['stem']}")

                # 放大影像後，每張圖下方也保留距離，避免和下一區塊文字太近
                st.markdown("<div style='height: 0.45rem;'></div>", unsafe_allow_html=True)


def show_intro_page():
    st.title("FFOCT 影像主觀評分系統")

    st.markdown(
        """
### 評分前參考：真實 FFOCT 與常見判讀範例

<div class="intro-text">
以下影像包含真實 FFOCT 的臉部與手部範例、SSOCT 外觀參考、偽影範例，以及皮膚層結構參考。<br>
請先觀察其整體外觀、表皮–真皮邊界、細胞核樣微結構與影像自然程度，再開始正式評分。
</div>

        """,
        unsafe_allow_html=True
    )

    if not os.path.isdir(EXAMPLE_DIR):
        st.warning(f"找不到範例資料夾：{EXAMPLE_DIR}")
        st.info("請建立資料夾 rating_dataset/example，並放入 face1-face3、hand1-hand3、SSOCT1-SSOCT3、偽影1-偽影3、facelayer1、handlayer1-handlayer2。")

    example_groups = get_example_groups()

    for group in example_groups:
        st.markdown(
            f"<div class='example-section-title'>{group['group_title']}</div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<div class='example-section-note'>{group['group_note']}</div>",
            unsafe_allow_html=True
        )
        st.markdown("<div style='height: 0.18rem;'></div>", unsafe_allow_html=True)

        # 第一頁除了最下面「FFOCT 皮膚層結構參考」維持原圖大小，
        # 其他範例影像皆放大 1.5 倍。
        if group["group_title"] == "FFOCT 皮膚層結構參考":
            render_example_items(group["items"], cols_per_row=3, image_scale=1.0)
        else:
            render_example_items(group["items"], cols_per_row=3, image_scale=1.5)

    st.markdown("<div style='height: 0.35rem;'></div>", unsafe_allow_html=True)

    btn_left, btn_right = st.columns([4.6, 1.5])
    with btn_right:
        st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)
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

    top_col1, top_col2, top_col3, top_col4 = st.columns([1.20, 1.05, 3.00, 1.35])

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

    left_col, right_col = st.columns([1.20, 3.10])

    with left_col:
        if os.path.exists(image_path):
            img = Image.open(image_path)

            st.markdown(
                f"<div class='region-badge'>部位：{region_label}</div>",
                unsafe_allow_html=True
            )
            st.caption(f"原始尺寸：{img.width} × {img.height}")
            st.markdown("<div style='height: 2px;'></div>", unsafe_allow_html=True)

            pad_l, img_col, pad_r = st.columns([0.08, 0.84, 0.08])
            with img_col:
                # 正式評分頁影像放大 1.5 倍，並與上方文字保留距離，避免卡到標籤與尺寸文字
                st.markdown("<div style='height: 0.55rem;'></div>", unsafe_allow_html=True)
                show_image_original(img, caption=image_id, scale=1.5)

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
