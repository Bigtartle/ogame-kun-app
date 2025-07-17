import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import os
import random
import sys

def main():
    """
    認証成功後に実行されるアプリ本体の関数
    """
    # --- セッション状態でデータを保持 ---
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'original_filename' not in st.session_state:
        st.session_state.original_filename = None

    # --- サイドバー ---
    with st.sidebar:
        st.header("設定")
        uploaded_file = st.file_uploader("データファイルを選択してください")
        st.divider()
        st.subheader("超音波吸収 (att)")
        sample_length_l_cm = st.number_input("試料長 l (cm)", value=0.5, step=1e-9, format="%.9f")
        att_run_button = st.button("超音波吸収を計算")
        st.divider()
        st.subheader("弾性定数相対変化 (ΔC/C)")
        sound_speed_v = st.number_input("音速 v (m/s)", value=3000.0, step=1e-9, format="%.9f")
        dc_run_button = st.button("弾性定数変化を計算")

    # --- ファイルがアップロードされたときの処理 ---
    if uploaded_file is not None:
        if uploaded_file.name != st.session_state.get('original_filename', None):
            st.session_state.original_filename = uploaded_file.name
            try:
                string_data = uploaded_file.getvalue().decode("shift_jis")
                lines = string_data.splitlines()
                header_line = lines[6].strip()
                column_names = re.split(r'\s{2,}', header_line)
                data_io = io.StringIO('\n'.join(lines[7:]))
                df = pd.read_csv(data_io, delim_whitespace=True, header=None, names=column_names)
                rename_dict = {}
                for col in df.columns:
                    if '(' in col and ')' in col:
                        new_col_name = col.split('(')[0].strip()
                        rename_dict[col] = new_col_name
                df.rename(columns=rename_dict, inplace=True)
                columns_to_drop = ['Rate', 'Vol_B', 'Phase', 'Amp']
                existing_columns_to_drop = [col for col in columns_to_drop if col in df.columns]
                if existing_columns_to_drop:
                    df = df.drop(columns=existing_columns_to_drop)
                st.session_state.df = df
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました: {e}")
                st.session_state.df = None
                st.session_state.original_filename = None

    # --- 計算ボタンの処理 ---
    if att_run_button and st.session_state.df is not None:
        try:
            df = st.session_state.df
            sin_col, cos_col = 'Sin', 'Cos'
            if sin_col in df.columns and cos_col in df.columns:
                sin_vals = df[sin_col].fillna(0).astype(float)
                cos_vals = df[cos_col].fillna(0).astype(float)
                amplitude_sq = sin_vals**2 + cos_vals**2
                amplitude_sq[amplitude_sq <= 0] = np.nan
                att_in_cm = -np.log(amplitude_sq) / (2 * sample_length_l_cm)
                df['att (1/cm)'] = att_in_cm.round(6)
                st.success("超音波吸収の計算が完了しました。")
        except Exception as e:
            st.error(f"超音波吸収の計算中にエラーが発生しました: {e}")

    if dc_run_button and st.session_state.df is not None:
        try:
            df = st.session_state.df
            sin_col, cos_col, freq_col = 'Sin', 'Cos', 'Freq'
            if all(c in df.columns for c in [sin_col, cos_col, freq_col]):
                phi = np.arctan2(df[sin_col].astype(float), df[cos_col].astype(float))
                unwrapped_phi = np.unwrap(phi)
                delta_phi = unwrapped_phi - unwrapped_phi[0]
                f_hz = df[freq_col].astype(float) * 1e6
                l_m = sample_length_l_cm / 100.0
                fai0 = (2 * np.pi * f_hz * l_m) / sound_speed_v
                fai0[fai0 == 0] = np.nan
                dc_per_c = -2 * delta_phi / fai0
                df['DC/C'] = dc_per_c
                st.success("弾性定数相対変化の計算が完了しました。")
        except Exception as e:
            st.error(f"弾性定数変化の計算中にエラーが発生しました: {e}")

    # --- メイン画面の表示 ---
    if st.session_state.df is not None:
        st.dataframe(st.session_state.df)
    else:
        st.info("ファイルをアップロードしてください。")

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
            output_text = st.session_state.df.to_csv(sep='\t', index=False)
            st.download_button(label="表示されている結果を保存", data=output_text.encode('utf-8-sig'), file_name=new_filename, mime='text/plain')

    # --- 豆知識コーナー ---
    st.divider()
    st.subheader("🔬 今日の超音波豆知識")
    trivia_list = [
        "コウモリやイルカは、超音波を使った反響定位で物体の位置を知る。", "医療のエコー検査は、超音波の反射で体の中を見る技術である。",
        "メガネ店の洗浄機は、超音波で発生した泡の力で汚れを落とす。", "潜水艦のソナーは、水中で超音波を発射して敵や地形を探知する。",
        "犬笛は、人間には聞こえない超音波を利用している。", "材料内部の傷を見つける「非破壊検査」にも超音波が使われる。"
    ]
    st.info(random.choice(trivia_list))

# --- ★★★★★ ここからがアプリ全体の起動ロジック ★★★★★ ---

st.set_page_config(page_title="OGAME-KUN", layout="wide")
st.title("*OGAME-KUN*")

# --- パスワード認証 ---
password = st.text_input("パスワードを入力してください", type="password")

if password == "OgameZen":  # 好きなパスワードに変更してください
    st.success("認証に成功しました。")
    main() # パスワードが正しい場合、アプリ本体の関数を実行
elif password: # 何か入力されているが、パスワードが違う場合
    st.warning("パスワードが違います。")
# パスワードが空の場合は何も表示しない