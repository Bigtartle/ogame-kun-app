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
                if 'current_mode' in st.session_state:
                    mode_option = st.session_state.current_mode
                else:
                    mode_option = "手動設定"
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
            
            # --- 測定モードの自動選択 ---
            st.header("3. 測定モードの自動選択")
            
            if analysis_method == "位相直交法":
                # 直交法にも自動選択ボタンを設置
                mode_option = st.radio(
                    "モードを選択すると列が自動割当されます",
                    ("手動設定", "温度一定磁場依存"),
                    key='current_mode'
                )
                
                # 直交法の自動割当ルール (Temp:2, B:0, Sin:5, Cos:6, Freq:7)
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
                # 自動設定された値を最優先でインデックス化し、ガードをかける
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
                
            # --- 磁場補正ボタンの処理 ---
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
                                scaling_factor = intended_range / actual_range
                                offset = intended_start_b - scaling_factor * actual_start_b
                                df[b_col_num] = (scaling_factor * b_col + offset).round(4)
                                st.success("磁場変化データの補正が完了しました。")
                                st.rerun()
                        elif correction_type == "一定磁場データ":
                            df[b_col_num] = intended_constant_b
                            st.success("一定磁場データの補正が完了しました。")
                            st.rerun()
                    else:
                        st.warning("割り当てられた磁場(B)の列が存在しません。")
                else:
                    st.warning("磁場(B)の列が「なし」に設定されているため、補正は実行できませんでした。")

            st.divider()
            st.header("6. 列の削除（オプション）")
            assigned_cols = [v for v in mappings.values() if v != 'なし']
            unassigned_cols = [c for c in df.columns if c not in assigned_cols]
            
            if mode_option != "手動設定":
                default_delete_cols = unassigned_cols
            else:
                default_delete_cols = []

            cols_to_delete = st.multiselect(
                "削除したい列（列番号）を選択", 
                options=unassigned_cols,
                default=default_delete_cols
            )
            
            # --- 列削除ボタンの処理 ---
            if st.button("選択した列を削除"):
                if cols_to_delete:
                    cols_to_delete_int = [int(c) for c in cols_to_delete]
                    df.drop(columns=cols_to_delete_int, inplace=True)
                    st.success(f"{len(cols_to_delete)}個の列を削除しました。")
                    st.rerun()

            st.divider()
            st.header("7. 計算パラメータと実行")
            
            if analysis_method == "位相直交法":
                sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
                sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
                echo_n = st.number_input("エコー位置 n", value=1, step=1, min_value=1)
                factor_2n_1 = 2 * echo_n - 1
                
                # --- 超音波吸収計算ボタン ---
                if st.button("超音波吸収を計算"):
                    try:
                        sin_col = mappings.get('Sin')
                        cos_col = mappings.get('Cos')
                        if sin_col != 'なし' and cos_col != 'なし':
                            sin_vals = df[sin_col].fillna(0).astype(float)
                            cos_vals = df[cos_col].fillna(0).astype(float)
                            amplitude_sq = sin_vals**2 + cos_vals**2
                            amplitude_sq[amplitude_sq <= 0] = np.nan
                            df['att (1/cm)'] = (-np.log(amplitude_sq) / (2 * sample_length_l_cm * factor_2n_1)).round(6)
                            st.success("超音波吸収の計算が完了しました。")
                            st.rerun()
                        else:
                            st.error("SinとCosの列を正しく割り当ててください。")
                    except Exception as e:
                        st.error(f"超音波吸収の計算中にエラーが発生しました: {e}")

                # --- 弾性定数変化計算ボタン ---
                if st.button("弾性定数変化を計算"):
                    try:
                        sin_col = mappings.get('Sin')
                        cos_col = mappings.get('Cos')
                        freq_col = mappings.get('Freq')
                        if all(c is not None and c != 'なし' for c in [sin_col, cos_col, freq_col]):
                            phi = np.arctan2(df[sin_col].astype(float), df[cos_col].astype(float))
                            delta_phi = np.unwrap(phi) - np.unwrap(phi)[0]
                            f_hz = df[freq_col].astype(float) * 1e6
                            l_m = sample_length_l_cm / 100.0
                            fai0 = (2 * np.pi * f_hz * l_m * factor_2n_1) / sound_speed_v
                            dc_per_c = (fai0**2 / (fai0 + delta_phi)**2) - 1
                            df['DC/C'] = dc_per_c
                            st.success("弾性定数相対変化の計算が完了しました。")
                            st.rerun()
                        else:
                            st.error("Sin, Cos, Freqの列を正しく割り当ててください。")
                    except Exception as e:
                        st.error(f"弾性定数変化の計算中にエラーが発生しました: {e}")
            
            elif analysis_method == "位相比較法":
                compare_freq_col = mappings.get('Freq')
                if compare_freq_col is not None and compare_freq_col in df.columns:
                    try:
                        default_f0 = float(df[compare_freq_col].iloc[0])
                    except Exception:
                        default_f0 = 19.2933
                else:
                    default_f0 = 19.2933

                f0_mhz = st.number_input("初期周波数 f₀ (MHz)", value=default_f0, step=1e-4, format="%.4f")
                
                # --- 弾性率相対変化（比較法）ボタン ---
                if st.button("弾性率相対変化を計算"):
                    try:
                        freq_col = mappings.get('Freq')
                        if freq_col is not None and freq_col != 'なし':
                            freq_mhz = df[freq_col].astype(float)
                            delta_f_over_f0 = (freq_mhz - f0_mhz) / f0_mhz
                            dc_per_c_comp = 2 * delta_f_over_f0 + (delta_f_over_f0)**2
                            df['DC/C'] = dc_per_c_comp
                            st.success("弾性率相対変化（比較法）の計算が完了しました。")
                            st.rerun()
                        else:
                            st.error("Freqの列を正しく割り当ててください。")
                    except Exception as e:
                        st.error(f"比較法の計算中にエラーが発生しました: {e}")

        # --- メイン画面のデータ表示 ---
        display_df = df.copy()
        inverse_mappings = {v: k for k, v in mappings.items() if v in display_df.columns and v != 'なし'}
        display_df.rename(columns=inverse_mappings, inplace=True)
        st.dataframe(display_df)

        # --- ダウンロードボタンの配置 ---
        with st.sidebar:
            st.divider()
            st.header("保存")
            if st.session_state.original_filename:
                base_name, _ = os.path.splitext(st.session_state.original_filename)
                new_filename = f"{base_name}(解析済み).txt"
            else:
                new_filename = "result.txt"
            
            output_df = df.copy()
            inv_map = {v: k for k, v in mappings.items() if v in output_df.columns and v != 'なし'}
            output_df.rename(columns=inv_map, inplace=True)
            output_text = output_df.to_csv(sep='\t', index=False)
            
            st.download_button(
                label="表示されている結果を保存", 
                data=output_text.encode('utf-8-sig'), 
                file_name=new_filename, 
                mime='text/plain'
            )
            
    else:
        st.info("ファイルをアップロードして、解析方法を選択してください。")

# --- アプリ全体の起動ロジック ---
st.set_page_config(page_title="OGAME-KUN", layout="wide")
st.title("OGAME-KUN")

if not st.session_state.get("authenticated", False):
    password = st.text_input("パスワードを入力してください", type="password")
    if password == "OgameZen":
        st.session_state.authenticated = True
        st.rerun()
    elif password:
        st.warning("パスワードが違います。")
else:
    main()
