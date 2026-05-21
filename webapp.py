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
        st.header("超音波実験データ解析")
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
            
            # --- 測定モードの選択 ---
            st.header("3. 測定モードの選択")
            if analysis_method == "位相比較法":
                measurement_mode = st.selectbox(
                    "測定モードを選択してください",
                    ("手動で列を割り当てる", "温度一定磁場依存", "磁場一定温度依存", "温度依存")
                )
            else:
                measurement_mode = "手動で列を割り当てる"

            # --- 自動処理の適用 ---
            mappings = st.session_state.column_mappings
            col_options = list(df_for_ui.columns)

            if measurement_mode == "温度一定磁場依存":
                # 自動割り当て (0: 磁場, 2: 温度, 3: 周波数)
                mappings['B'] = 0
                mappings['Temp'] = 2
                mappings['Freq'] = 3
                
                # 安全対策：裏でのデータ破壊（列削除）はやめてアナウンスのみにする
                st.success("【自動設定完了】\n- 0番: 磁場 (B)\n- 2番: 温度 (Temp)\n- 3番: 周波数 (Freq)")

            # --- 列の割り当てUIを表示するセクション ---
            st.divider()
            st.subheader("列の割り当て（確認・調整）")
            st.write("現在の列の割り当て状況です。必要に応じて変更できます。")
            b_col_options = ["なし"] + col_options

            def get_index(key, default_index=0, options=col_options):
                safe_default_index = min(default_index, len(options) - 1)
                value_to_find = mappings.get(key, options[safe_default_index])
                if value_to_find not in options:
                    return 0
                return options.index(value_to_find)

            if analysis_method == "位相直交法":
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', 0))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 3,
