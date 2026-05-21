import streamlit as st
import pandas as pd
import numpy as np
import io
import os

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
                
                # Pandasでの動作を保証するため sep=r'\s+' を使用
                df = pd.read_csv(data_io, sep=r'\s+', header=None, engine='python')
                
                st.session_state.df = df
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
            st.header("3. 列の割り当て")
            st.write("表の列番号を、対応するデータの種類に割り当ててください。")
            
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
            st.header("5. 列の削除（オプション）")
            assigned_cols = [v for v in mappings.values() if v != 'なし']
            unassigned_cols = [c for c in df.columns if c not in assigned_cols]
            cols_to_delete = st.multiselect("削除したい列（列番号）を選択", options=unassigned_cols)
            
            # --- 列削除ボタンの処理 ---
            if st.button("選択した列を削除"):
                if cols_to_delete:
                    cols_to_delete_int = [int(c) for c in cols_to_delete]
                    df.drop(columns=cols_to_delete_int, inplace=True)
                    st.success(f"{len(cols_to_delete)}個の列を削除しました。")
                    st.rerun()

            st.divider()
            st.header("6. 計算パラメータと実行")
            
            if analysis_method == "位相直交法":
                sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
                sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
                
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
                            df['att (1/cm)'] = (-np.log(amplitude_sq) / (2 * sample_length_l_cm)).round(6)
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
                            fai0 = (2 * np.pi * f_hz * l_m) / sound_speed_v
                            dc_per_c = (fai0**2 / (fai0 + delta_phi)**2) - 1
                            df['DC/C'] = dc_per_c
                            st.success("弾性定数相対変化の計算が完了しました。")
                            st.rerun()
                        else:
                            st.error("Sin, Cos, Freqの列を正しく割り当ててください。")
                    except Exception as e:
                        st.error(f"弾性定数変化の計算中にエラーが発生しました: {e}")
            
            elif analysis_method == "位相比較法":
                f0_mhz = st.number_input("初期周波数 f₀ (MHz)", value=19.2933, step=1e-4, format="%.4f")
                
                # --- 弾性率相対変化（比較法）ボタン ---
                if st.button("弾性率相対変化を計算"):
                    try:
                        freq_col = mappings.get('Freq')
                        if freq_col is not None and freq_col != 'なし':
                            freq_mhz = df[freq_col].astype(float)
                            delta_f_over_f0 = (freq_mhz - f0_mhz) / f0_mhz
                            dc_per_c_comp = 2 * delta_f_over_f0 + (delta_f_over_f0)**2
                            df['DC/C (比較法)'] = dc_per_c_comp
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
