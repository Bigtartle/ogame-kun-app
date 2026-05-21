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
                
                # 指定列（0, 2, 3）以外の列を自動で削除（切れないよう改行調整）
                keep_cols = [0, 2, 3]
                cols_to_drop = [c for c in df_for_ui.columns if c not in keep_cols]
                if cols_to_drop:
                    st.session_state.df.drop(
                        columns=cols_to_drop, 
                        inplace=True
                    )
                    st.toast("指定された列以外を自動削除しました！", icon="✂️")
                
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
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 3, b_col_options))
                mappings['Sin'] = st.selectbox("Sin(V) の列", col_options, index=get_index('Sin', 6))
                mappings['Cos'] = st.selectbox("Cos(V) の列", col_options, index=get_index('Cos', 7))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', 8))
            
            elif analysis_method == "位相比較法":
                # モードが未実装のものはデフォルトのインデックスを適用
                default_temp_idx = 2 if measurement_mode == "温度一定磁場依存" else 0
                default_b_idx = 0 if measurement_mode == "温度一定磁場依存" else 3
                default_freq_idx = 3 if measurement_mode == "温度一定磁場依存" else 4
                
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', default_temp_idx))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', default_b_idx, b_col_options))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', default_freq_idx))

            # --- 手動列削除UI ---
            if measurement_mode == "手動で列を割り当てる" or measurement_mode in ["磁場一定温度依存", "温度依存"]:
                st.divider()
                st.subheader("列の削除（オプション）")
                assigned_cols = [v for v in mappings.values() if v != 'なし']
                unassigned_cols = [c for c in df_for_ui.columns if c not in assigned_cols]
                cols_to_delete = st.multiselect("削除したい列（列番号）を選択", options=unassigned_cols)
                if st.button("選択した列を削除"):
                    if cols_to_delete:
                        cols_to_delete_int = [int(c) for c in cols_to_delete]
                        st.session_state.df.drop(columns=cols_to_delete_int, inplace=True)
                        st.success(f"{len(cols_to_delete)}個の列を削除しました。")
                        st.rerun()

            st.divider()
            st.header("4. 磁場補正（オプション）")
            correction_type = st.radio("補正の種類を選択", ("磁場変化データ", "一定磁場データ"))
            if correction_type == "磁場変化データ":
                intended_start_b = st.number_input("本来の開始磁場 (T)", value=0.0, step=0.5)
                intended_end_b = st.number_
