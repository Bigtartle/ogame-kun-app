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

    # --- ファイルがアップロードされたときの処理 ---
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get('original_filename', None):
            st.session_state.original_filename = uploaded_file.name
            try:
                string_data = uploaded_file.getvalue().decode("shift_jis")
                lines = string_data.splitlines()
                data_start_index = 0
                for i, line in enumerate(lines):
                    try:
                        if len(line.strip().split()) > 2:
                            [float(x) for x in line.strip().split() if x.lower() != 'nan']
                            data_start_index = i
                            break
                    except (ValueError, IndexError):
                        continue
                data_io = io.StringIO('\n'.join(lines[data_start_index:]))
                
                df = pd.read_csv(data_io, sep=r'\s+', header=None, engine='python')
                
                st.session_state.df = df
                if 'current_mode' not in st.session_state:
                    st.session_state.column_mappings = {} 
                st.rerun()
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                st.session_state.df = None
                st.session_state.original_filename = None

    # --- データが存在する場合の処理（UI構築＆各種計算） ---
    if st.session_state.df is not None:
        df = st.session_state.df
        mappings = st.session_state.column_mappings
        col_options = list(df.columns)
        b_col_options = ["なし"] + col_options

        # サイドバーの続きのUI項目を配置
        with st.sidebar:
            st.divider()
            
            # --- 3. 測定モードの自動選択 ---
            st.header("3. 測定モードの自動選択")
            
            if analysis_method == "位相直交法":
                mode_option = st.radio(
                    "モードを選択すると列が自動割当されます",
                    ("手動設定", "温度一定磁場依存"),
                    key='current_mode'
                )
                if mode_option == "温度一定磁場依存":
                    mappings['Temp'] = 2
                    mappings['B'] = 0
                    mappings['Sin'] = 5
                    mappings['Cos'] = 6
                    mappings['Freq'] = 7

            elif analysis_method == "位相比較法":
                mode_option = st.radio(
                    "モードを選択すると列が自動割当されます",
                    ("手動設定", "無磁場温度依存", "磁場一定温度依存", "温度一定磁場依存"),
                    key='current_mode'
                )
                if mode_option == "無磁場温度依存":
                    mappings['Temp'] = 0
                    mappings['B'] = "なし"
                    mappings['Freq'] = 2
                elif mode_option == "磁場一定温度依存":
                    mappings['Temp'] = 0
                    mappings['B'] = 2
                    mappings['Freq'] = 4
                elif mode_option == "温度一定磁場依存":
                    mappings['Temp'] = 2
                    mappings['B'] = 0
                    mappings['Freq'] = 3

            st.divider()
            st.header("4. 列の割り当て確認")
            
            if mode_option != "手動設定":
                st.caption("⚠️自動モード有効中（列は固定されています）")
                is_disabled = True
            else:
                st.write("表の列番号を割り当ててください。")
                is_disabled = False
            
            def get_index(key, default_index=0, options=col_options):
                safe_default_index = min(default_index, len(options) - 1)
                value_to_find = mappings.get(key, options[safe_default_index])
                if value_to_find not in options:
                    return 0
                return options.index(value_to_find)

            if analysis_method == "位相直交法":
                val_t = mappings.get('Temp', 2)
                val_b = mappings.get('B', 0)
                val_sin = mappings.get('Sin', 5)
                val_cos = mappings.get('Cos', 6)
                val_f = mappings.get('Freq', 7)
                
                idx_t = col_options.index(val_t) if val_t in col_options else 0
                idx_b = b_col_options.index(val_b) if val_b in b_col_options else 0
                idx_sin = col_options.index(val_sin) if val_sin in col_options else 0
                idx_cos = col_options.index(val_cos) if val_cos in col_options else 0
                idx_f = col_options.index(val_f) if val_f in col_options else 0

                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=idx_t, disabled=is_disabled)
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=idx_b, disabled=is_disabled)
                mappings['Sin'] = st.selectbox("Sin(V) の列", col_options, index=idx_sin, disabled=is_disabled)
                mappings['Cos'] = st.selectbox("Cos(V) の列", col_options, index=idx_cos, disabled=is_disabled)
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=idx_f, disabled=is_disabled)
            
            elif analysis_method == "位相比較法":
                val_t = mappings.get('Temp', 0)
                val_b = mappings.get('B', "なし")
                val_f = mappings.get('Freq', 4)
                
                idx_t = col_options.index(val_t) if val_t in col_options else 0
                idx_b = b_col_options.index(val_b) if val_b in b_col_options else 0
                idx_f = col_options.index(val_f) if val_f in col_options else 0

                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=idx_t, disabled=is_disabled)
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=idx_b, disabled=is_disabled)
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=idx_f, disabled=is_disabled)

            st.divider()
            st.header("5. 磁場補正（オプション）")
            correction_type = st.radio("補正の種類を選択", ("磁場変化データ", "一定磁場データ"))
            if correction_type == "磁場変化データ":
                intended_start_b = st.number_input("本来の開始磁場 (T)", value=0.0, step=0.5)
                intended_end_b = st.number_input("本来の終了磁場 (T)", value=3.0, step=0.5)
            else:
                intended_constant_b = st.number_input("本来かけた磁場 (T)", value=0.0, step=0.5)
                
            if st.button("磁場データを補正"):
                b_col_name = mappings.get('B')
                if b_col_name is not None and b_col_name != 'なし':
                    b_col_num = int(b_col_name)
                    if b_col_num in df.columns:
                        b_col = df[b_col_num].astype(float)
                        if correction_type == "磁場変化データ":
                            actual_start_b, actual_end_b = b_col.iloc[0], b_col.iloc[-1]
                            actual_range = actual_end_b - actual_start_b
                            intended_range = intended_end_b - intended_start_b
                            if actual_range != 0:
                                scaling_factor = intended
