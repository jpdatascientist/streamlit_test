import streamlit as st
import openai
import os
import fitz  # PyMuPDF for PDF
import docx  # python-docx for Word

# --- ページ設定 ---
st.set_page_config(
    page_title="生成・校閲アプリケーション",
    page_icon="📝",
    layout="wide"
)

# --- OpenAI SDKバージョン確認 ---
try:
    st.sidebar.write(f"OpenAI SDK バージョン: {openai.__version__}")
except Exception as e:
    st.sidebar.write("OpenAI SDKバージョンを確認できません")

# --- APIキー読み込み ---
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error("OpenAI APIキーがSecretsに設定されていません。Streamlit Cloudの「Secrets」メニューで設定してください。")
    st.error(f"エラー詳細: {e}")
    st.stop()

openai.api_key = api_key

# --- サイドバー設定 ---
with st.sidebar:
    st.title("機能選択")
    app_mode = st.radio("モードを選択してください:", ["テキスト生成", "テキスト校閲"])
    st.divider()

    model = st.selectbox("使用するモデル:", ["gpt-4o-mini", "gpt-4o"], index=0)
    temperature = st.slider("温度 (クリエイティビティ)", 0.0, 1.0, 0.7, 0.1)
    st.divider()
    st.write("生成・校閲アプリケーション")

# --- メイン ---
st.title("生成・校閲アプリケーション")

# === テキスト生成 ===
if app_mode == "テキスト生成":
    st.header("テキスト生成")
    prompt_type = st.selectbox("生成するテキストのタイプ:", ["メールマガジン", "SMS", "SNS投稿"])
    topic = st.text_input("トピックや主題:")
    length = st.select_slider("文章の長さ:", options=["短め (100字程度)", "標準 (300字程度)", "長め (500字程度)", "詳細 (1000字以上)"])
    additional_info = st.text_area("追加情報や要望があれば入力してください:")

    if st.button("生成する", type="primary"):
        if not topic:
            st.warning("トピックを入力してください。")
        else:
            with st.spinner("AIが文章を生成中..."):
                prompt = f"""
                次の条件に合うテキストを生成してください:
                - タイプ: {prompt_type}
                - トピック: {topic}
                - 長さ: {length}
                - 追加情報: {additional_info}

                日本語で自然な文章を生成してください。
                """

                try:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                    )
                    result = response.choices[0].message.content

                    st.success("テキストが生成されました！")
                    st.text_area("生成されたテキスト:", result, height=300)

                    st.download_button(
                        label="テキストをダウンロード",
                        data=result,
                        file_name=f"{topic}_generated_text.txt",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")

# === テキスト校閲 ===
elif app_mode == "テキスト校閲":
    st.header("テキスト校閲")

    input_mode = st.radio("入力方法を選択してください", ["テキストを直接入力", "PDFまたはWordファイルをアップロード"])
    input_text = ""

    if input_mode == "テキストを直接入力":
        input_text = st.text_area("校閲したいテキストを入力してください:", height=200)
    else:
        uploaded_file = st.file_uploader("ファイルをアップロード（PDFまたはWord）", type=["pdf", "docx"])
        if uploaded_file:
            file_size_mb = len(uploaded_file.read()) / (1024 * 1024)
            uploaded_file.seek(0)  # ファイルポインタをリセット

            if file_size_mb > 200:
                st.error("200MBを超えるファイルはアップロードできません。")
            else:
                if uploaded_file.name.endswith(".pdf"):
                    try:
                        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
                        input_text = "\n".join([page.get_text() for page in doc])
                        st.success("PDFファイルの内容を抽出しました。")
                    except Exception as e:
                        st.error(f"PDFの読み込みに失敗しました: {e}")
                elif uploaded_file.name.endswith(".docx"):
                    try:
                        docx_file = docx.Document(uploaded_file)
                        input_text = "\n".join([para.text for para in docx_file.paragraphs])
                        st.success("Wordファイルの内容を抽出しました。")
                    except Exception as e:
                        st.error(f"Wordファイルの読み込みに失敗しました: {e}")

    check_options = st.multiselect(
        "確認項目:",
        ["景品表示法への抵触がないか", "金融商品取引法への抵触がないか", "文法", "スペル", "わかりやすさ", "一貫性"]
    )

    if st.button("校閲する", type="primary"):
        if not input_text.strip():
            st.warning("校閲するテキストが空です。")
        else:
            with st.spinner("AIが校閲中..."):
                checks = ", ".join(check_options) if check_options else "すべての側面"

                prompt = f"""
                以下のテキストを校閲してください。{checks}に注目して改善点を指摘し、
                修正案を提案してください。元のテキストを尊重しつつ、より明確で効果的な表現を目指してください。

                テキスト:
                {input_text}

                以下の形式で回答してください：
                1. 全体的な評価
                2. 具体的な改善点（元の文と修正案を対比）
                3. 修正後の全文
                """

                try:
                    response = openai.ChatCompletion.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                    )
                    result = response.choices[0].message.content

                    st.success("校閲が完了しました！")
                    tab1, tab2 = st.tabs(["校閲結果", "比較"])
                    with tab1:
                        st.markdown(result)
                    with tab2:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("元のテキスト")
                            st.text_area("", input_text, height=300)
                        with col2:
                            st.subheader("校閲後の提案")
                            st.text_area("", result, height=300)

                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")

# --- フッター ---
st.markdown("---")
st.markdown("このアプリケーションは主としてOpenAI GPT-4o-mini APIを使用しています。生成されたテキストは参考用途にのみご利用ください。")