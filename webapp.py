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
            "解析方法を選択",
            ("位相直交法", "位相比較法"),
            key='analysis_method'
        )
        
        # 2. ファイルアップローダー
        uploaded_file = st.file_uploader("データファイルを選択してください")

        # --- ファイルがアップロードされた後、UIを表示 ---
        if st.session_state.df is not None:
            df_for_ui = st.session_state.df
            st.divider()
            st.header("列の割り当て")
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

            # --- 解析方法に応じて列の割り当てUIを変更 ---
            if st.session_state.analysis_method == "位相直交法":
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', 0))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 2, b_col_options))
                mappings['Sin'] = st.selectbox("Sin(V) の列", col_options, index=get_index('Sin', 6))
                mappings['Cos'] = st.selectbox("Cos(V) の列", col_options, index=get_index('Cos', 7))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', 8))
            
            elif st.session_state.analysis_method == "位相比較法":
                mappings['Temp'] = st.selectbox("温度 (Temp) の列", col_options, index=get_index('Temp', 0))
                mappings['B'] = st.selectbox("磁場 (B) の列", b_col_options, index=get_index('B', 2, b_col_options))
                mappings['Freq'] = st.selectbox("周波数 (Freq) の列", col_options, index=get_index('Freq', 4))

            st.divider()
            
            st.header("磁場補正（オプション）")
            correction_type = st.radio(
                "補正の種類を選択",
                ("磁場変化データ", "一定磁場データ"),
                help="磁場変化：0T⇄3Tのように磁場を変化させたデータ。一定磁場：特定の磁場で温度を変化させたデータ。"
            )
            if correction_type == "磁場変化データ":
                intended_start_b = st.number_input("本来の開始磁場 (T)", value=0.0, step=0.5)
                intended_end_b = st.number_input("本来の終了磁場 (T)", value=3.0, step=0.5)
            else:
                intended_constant_b = st.number_input("本来かけた磁場 (T)", value=0.0, step=0.5)
            correction_button = st.button("磁場データを補正")

            st.divider()
            
            st.header("列の削除（オプション）")
            assigned_cols = [v for v in mappings.values() if v != 'なし']
            unassigned_cols = [c for c in df_for_ui.columns if c not in assigned_cols]
            cols_to_delete = st.multiselect("削除したい列（列番号）を選択", options=unassigned_cols)
            delete_button = st.button("選択した列を削除")

            st.divider()
            st.header("計算パラメータと実行")
            
            if st.session_state.analysis_method == "位相直交法":
                st.session_state.sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
                st.session_state.sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
                att_run_button = st.button("超音波吸収を計算")
                dc_run_button = st.button("弾性定数変化を計算")
            
            elif st.session_state.analysis_method == "位相比較法":
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
                df = pd.read_csv(data_io, delim_whitespace=True, header=None)
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

        if 'delete_button' in locals() and delete_button:
            if cols_to_delete:
                cols_to_delete_int = [int(c) for c in cols_to_delete]
                df.drop(columns=cols_to_delete_int, inplace=True)
                st.success(f"{len(cols_to_delete)}個の列を削除しました。")
                st.rerun()
        
        if 'correction_button' in locals() and correction_button:
            b_col_name = mappings.get('B')
            if b_col_name is not None and b_col_name != 'なし':
                b_col_num = int(b_col_name)
                if b_col_num in df.columns:
                    b_col = df[b_col_num].astype(float)
                    if correction_type == "磁場変化データ":
                        actual_start_b = b_col.iloc[0]
                        actual_end_b = b_col.iloc[-1]
                        actual_range = actual_end_b - actual_start_b
                        intended_range = intended_end_b - intended_start_b
                        if actual_range != 0:
                            scaling_factor_a = intended_range / actual_range
                            offset_b = intended_start_b - scaling_factor_a * actual_start_b
                            df[b_col_num] = (scaling_factor_a * b_col + offset_b).round(4)
                            st.success("磁場変化データの補正が完了しました。")
                    elif correction_type == "一定磁場データ":
                        df[b_col_num] = intended_constant_b
                        st.success("一定磁場データの補正が完了しました。")
                else:
                    st.warning("割り当てられた磁場(B)の列が存在しません。")
            else:
                st.warning("磁場(B)の列が「なし」に設定されているため、補正は実行できませんでした。")

        if 'att_run_button' in locals() and att_run_button:
            try:
                sin_col = mappings.get('Sin')
                cos_col = mappings.get('Cos')
                if sin_col != 'なし' and cos_col != 'なし':
                    sin_vals = df[sin_col].fillna(0).astype(float)
                    cos_vals = df[cos_col].fillna(0).astype(float)
                    amplitude_sq = sin_vals**2 + cos_vals**2
                    amplitude_sq[amplitude_sq <= 0] = np.nan
                    att_in_cm = -np.log(amplitude_sq) / (2 * st.session_state.sample_length_l_cm)
                    df['att (1/cm)'] = att_in_cm.round(6)
                    st.success("超音波吸収の計算が完了しました。")
                else:
                    st.error("SinとCosの列を正しく割り当ててください。")
            except Exception as e:
                st.error(f"超音波吸収の計算中にエラーが発生しました: {e}")

        if 'dc_run_button' in locals() and dc_run_button:
            try:
                sin_col = mappings.get('Sin')
                cos_col = mappings.get('Cos')
                freq_col = mappings.get('Freq')
                if all(c is not None and c != 'なし' for c in [sin_col, cos_col, freq_col]):
                    phi = np.arctan2(df[sin_col].astype(float), df[cos_col].astype(float))
                    unwrapped_phi = np.unwrap(phi)
                    delta_phi = unwrapped_phi - unwrapped_phi[0]
                    f_hz = df[freq_col].astype(float) * 1e6
                    l_m = st.session_state.sample_length_l_cm / 100.0
                    fai0 = (2 * np.pi * f_hz * l_m) / st.session_state.sound_speed_v
                    fai0[fai0 == 0] = np.nan
                    dc_per_c = -2 * delta_phi / fai0
                    df['DC/C'] = dc_per_c
                    st.success("弾性定数相対変化の計算が完了しました。")
                else:
                    st.error("Sin, Cos, Freqの列を正しく割り当ててください。")
            except Exception as e:
                st.error(f"弾性定数変化の計算中にエラーが発生しました: {e}")

        if 'compare_method_button' in locals() and compare_method_button:
            try:
                freq_col = mappings.get('Freq')
                if freq_col is not None and freq_col != 'なし':
                    freq_mhz = df[freq_col].astype(float)
                    f0_mhz_val = st.session_state.f0_mhz
                    delta_f_over_f0 = (freq_mhz - f0_mhz_val) / f0_mhz_val
                    dc_per_c_comp = -1 * delta_f_over_f0
                    df['DC/C (比較法)'] = dc_per_c_comp
                    st.success("弾性率相対変化（比較法）の計算が完了しました。")
                else:
                    st.error("Freqの列を正しく割り当ててください。")
            except Exception as e:
                st.error(f"比較法の計算中にエラーが発生しました: {e}")
        
    # --- メイン画面の表示 ---
    if st.session_state.df is not None:
        display_df = st.session_state.df.copy()
        inverse_mappings = {v: k for k, v in st.session_state.column_mappings.items() if v in display_df.columns and v != 'なし'}
        display_df.rename(columns=inverse_mappings, inplace=True)
        
        with st.sidebar:
            st.divider()
            st.header("表示設定")
            all_display_cols = list(display_df.columns)
            default_cols = [col for col in all_display_cols if col not in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]] # 計算結果と割り当てた列をデフォルト表示
            selected_cols = st.multiselect("表示する列を選択", options=all_display_cols, default=default_cols)
        
        if selected_cols:
            st.dataframe(display_df[selected_cols])
        else:
            st.warning("表示する列が選択されていません。")
    else:
        st.info("ファイルをアップロードして、解析方法を選択してください。")

    # --- ダウンロードボタン ---
    with st.sidebar:
        if st.session_state.df is not None:
            st.divider()
            st.header("保存")
            if st.session_state.original_filename:
                base_name, _ = os.path.splitext(st.session_state.original_filename)
                new_filename = f"{base_name}(解析済み).txt"
            else:
                new_filename = "result.txt"
            
            output_df = st.session_state.df.copy()
            inv_map = {v: k for k, v in st.session_state.column_mappings.items() if v in output_df.columns and v != 'なし'}
            output_df.rename(columns=inv_map, inplace=True)
            output_text = output_df.to_csv(sep='\t', index=False)
            
            st.download_button(label="表示されている結果を保存", data=output_text.encode('utf-8-sig'), file_name=new_filename, mime='text/plain')
    
# --- アプリ全体の起動ロジック ---
st.set_page_config(page_title="OGAME-KUN", layout="wide")
st.title("*OGAME-KUN*")

if not st.session_state.get("authenticated", False):
    password = st.text_input("パスワードを入力してください", type="password")
    if password == "OgameZen":
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.warning("パスワードが違います。")
else:
    main()