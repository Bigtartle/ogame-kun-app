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
            
            # --- 【新機能】測定モードの選択 ---
            st.header("3. 測定モードの選択")
            if analysis_method == "位相比較法":
                measurement_mode = st.selectbox(
                    "測定モードを選択してください",
                    ("手動で列を割り当てる", "温度一定磁場依存", "磁場一定温度依存", "温度依存")
                )
            else:
                # 位相直交法は現時点で手動のみ
                measurement_mode = "手動で列を割り当てる"

            # --- 自動処理の適用 ---
            mappings = st.session_state.column_mappings
            col_options = list(df_for_ui.columns)

            if measurement_mode == "温度一定磁場依存":
                # 自動割り当て (0: 磁場, 2: 温度, 3: 周波数)
                mappings['B'] = 0
                mappings['Temp'] = 2
                mappings['Freq'] = 3
                
                # 指定列（0, 2, 3）以外の列を自動で削除
                keep_cols = [0, 2, 3]
                cols_to_drop = [c for c in df_for_ui.columns if c not in keep_cols]
                if cols_to_drop:
                    st.session_state.df.drop(columns=cols_to_drop, inplace=True)
                    st.toast("指定された列以外を自動削除しました！", icon="✂️")
                
                st.success("【自動設定完了】\n- 0番: 磁場 (B)\n- 2番: 温度 (Temp)\n- 3番: 周波数 (Freq)")

            elif measurement_mode == "手動で列を割り当てる":
                # 従来通りの手動選択 UI
                st.subheader("列の割り当て")
                st.write("表の列番号を、対応するデータの種類に割り当ててください。")
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
            else:
                # まだロジックを作っていないモード
                st.warning("このモードの自動割り当てロジックは未実装です。")

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
            st.header("5. 計算パラメータと実行")
            
            if analysis_method == "位相直交法":
                st.session_state.sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
                st.session_state.sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
                att_run_button = st.button("超音波吸収を計算")
                dc_run_button = st.button("弾性定数変化を計算")
            
            elif analysis_method == "位相比較法":
                st.session_state.f0_mhz = st.number_input("初期周波数 f₀ (MHz)", value=19.2933, step=1e-4, format="%.4f")
                compare_method_button = st.button("弾性率相対変化を計算")

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
                st.session_state.column_mappings = {} 
                st.rerun()
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                st.session_state.df = None
                st.session_state.original_filename = None

    # --- ボタン処理 ---
    if 'df' in st.session_state and st.session_state.df is not None:
        df = st.session_state.df
        mappings = st.session_state.column_mappings
        
        if 'correction_button' in locals() and correction_button:
            b_col_name = mappings.get('B')
            if b_col_name is not None and b_col_name != 'なし':
                b_col_num = int(b_col_name)
                if b_col_num in df.columns:
                    b_col = df[b_col_num].astype(float)
                    if 'correction_type' in locals() and correction_type == "磁場変化データ":
                        actual_start_b, actual_end_b = b_col.iloc[0], b_col.iloc[-1]
                        actual_range, intended_range = actual_end_b - actual_start_b, intended_end_b - intended_start_b
                        if actual_range != 0:
                            scaling_factor = intended_range / actual_range
                            offset = intended_start_b - scaling_factor * actual_start_b
                            df[b_col_num] = (scaling_factor * b_col + offset).round(4)
                            st.success("磁場変化データの補正が完了しました。")
                    elif 'correction_type' in locals() and correction_type == "一定磁
