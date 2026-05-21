import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import random
import sys

# --- セッション状態の初期化 ---
if 'df' not in st.session_state:
    st.session_state.df = None
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if 'column_mappings' not in st.session_state:
    st.session_state.column_mappings = {}

def main():
    """
    認証成功後に実行されるアプリ本体の関数
    """
    # --- サイドバー ---
    with st.sidebar:
        st.header("設定")
        # 1. 解析方法を最初に選択
        analysis_method = st.radio(
            "1. 解析方法を選択",
            ("位相直交法", "位相比較法"),
            key='analysis_method'
        )
        
        # 2. ファイルアップローダー
        uploaded_file = st.file_uploader("2. データファイルを選択")

        # --- ファイルがアップロードされた後、UIを表示 ---
        if st.session_state.df is not None:
            df_for_ui = st.session_state.df
            st.divider()
            st.header("3. 列の割り当て")
            st.write("表の列番号を、対応するデータの種類に割り当ててください。")
            
            col_options = list(df_for_ui.columns)
            mappings = st.session_state.column_mappings
            
            b_col_options = ["なし"] + col_options

            def get_index(key, default_index=0, options=col_options):
                safe_default_index = min(default_index, len(options) - 1)
                value_to_find = mappings.get(key, options[safe_default_index])
                if value_to_find not in options:
                    return 0
                return options.index(value_to_find)

            if analysis_method == "位相直交法":
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', 0))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 3, b_col_options))
                mappings['Sin'] = st.selectbox("Sin(V) の列", col_options, index=get_index('Sin', 6))
                mappings['Cos'] = st.selectbox("Cos(V) の列", col_options, index=get_index('Cos', 7))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', 8))
            
            elif analysis_method == "位相比較法":
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', 0))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 3, b_col_options))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', 4))

            st.divider()
            
            st.header("4. 磁場補正（オプション）")
            correction_type = st.radio("補正の種類を選択", ("磁場変化データ", "一定磁場データ"))
            if correction_type == "磁場変化データ":
                intended_start_b = st.number_input("本来の開始磁場 (T)", value=0.0, step=0.5)
                intended_end_b = st.number_input("本来の終了磁場 (T)", value=3.0, step=0.5)
            else:
                intended_constant_b = st.number_input("本来かけた磁場 (T)", value=0.0, step=0.5)
            correction_button = st.button("磁場データを補正")

            st.divider()
            
            st.header("5. 列の削除（オプション）")
            assigned_cols = [v for v in mappings.values() if v != 'なし']
            unassigned_cols = [c for c in df_for_ui.columns if c not in assigned_cols]
            cols_to_delete = st.multiselect("削除したい列（列番号）を選択", options=unassigned_cols)
            delete_button = st.button("選択した列を削除")

            st.divider()
            st.header("6. 計算パラメータと実行")
            
            if analysis_method == "位相直交法":
                st.session_state.sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
                st.session_state.sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
                att_run_button = st.button("超音波吸収を計算")
                dc_run_button = st.button("弾性定数変化を計算")
            
            elif analysis_method == "位相比較法":
                st.session_state.f0_mhz = st.number_input("初期周波数 f₀ (MHz)", value=19.2933, step=1e-4, format="%.4f")
                compare_method_button = st.button("弾性率相対変化を計算")
