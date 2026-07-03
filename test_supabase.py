# -*- coding: utf-8 -*-
import streamlit as st
from supabase import create_client

@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_KEY"]
    )

st.title("Supabase 寫入測試")

supabase = get_supabase_client()

test_row = {
    "expert_id": "test_expert",
    "image_id": "Image_test",
    "region": "test_region",
    "case_id": "test_case",
    "case_number": 0,
    "method": "test_method",
    "overall_score": 1,
    "layer_score": 2,
    "nucleus_score": 3,
    "artifact_score": 4
}

try:
    response = supabase.table("ratings").upsert(
        test_row,
        on_conflict="expert_id,image_id"
    ).execute()

    st.success("成功寫入 Supabase ratings 資料表")
    st.write(response.data)

except Exception as e:
    st.error("寫入失敗")
    st.exception(e)