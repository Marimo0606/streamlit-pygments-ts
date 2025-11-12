import re
import html
from typing import List, Tuple

import streamlit as st
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter, BBCodeFormatter
from pygments.styles import get_all_styles

# Streamlit page config
st.set_page_config(page_title="Pygments ハイライト (Streamlit)", layout="wide")

# ヘッダ
st.title("テキスト内のPythonコードをPygmentsでハイライト")
st.markdown(
    "テキスト中のコードは次のデリミタで囲んでください：\n\n"
    "`◆→開始:Pythonコード←◆` と `◆→終了:Pythonコード←◆`"
)

# 入力方法
col1, col2 = st.columns([3, 1])
with col1:
    uploaded = st.file_uploader("テキストファイルをアップロード (省略可)", type=["txt", "md"])
    # text_area にキーを付けて session_state 経由で値を扱いやすくする
    text_input = st.text_area(
        "またはここにテキストを貼り付けてください（アップロードが優先されます）。「ハイライト実行」をクリックすると色を確認できます",
        height=300,
        placeholder="ここにテキストを貼り付け...",
        key="text_input",
    )

    # サンプル読み込みボタン（ここで session_state にセットしてから下で raw を決定する）
    if st.button("サンプルを読み込む"):
        sample = (
            "これはサンプルのテキストです。\n\n"
            "普通の文章が続きます。\n\n"
            "◆→開始:Pythonコード←◆\n"
            "def hello(name):\n"
            "    print(f\"Hello, {name}!\")\n\n"
            "for i in range(3):\n"
            "    hello('world')\n"
            "◆→終了:Pythonコード←◆\n\n"
            "また普通の文章に戻ります。\n"
        )
        # セッションに格納して、この実行フロー内で使えるようにする
        st.session_state["sample_raw"] = sample

with col2:
    st.markdown("表示スタイル")
    try:
        styles = sorted(list(get_all_styles()))
    except Exception:
        styles = ["friendly", "default", "monokai", "colorful", "autumn"]
    default_index = styles.index("friendly") if "friendly" in styles else 0
    style = st.selectbox("Pygments スタイル", options=styles, index=default_index)

    st.markdown("出力")
    download_html = st.checkbox("ハイライト結果を .html としてダウンロードする", value=False)
    download_txt = st.checkbox("ハイライト結果を .txt（BBCode）でダウンロードする", value=True)
    st.markdown("---")
    st.markdown("注意")
    st.caption(
        "サードパーティ製のスタイル（例: kmuto/pygments-style-texlistings）を使いたい場合は "
        "requirements.txt にそのパッケージを追加してから Streamlit Community Cloud にデプロイしてください。"
    )

# 優先的にアップロードされたファイルを使う
if uploaded is not None:
    try:
        raw = uploaded.read().decode("utf-8")
    except Exception:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
else:
    # まずサンプル（button が押された場合は session_state に入る）を優先、その次にテキストエリアを使う
    raw = st.session_state.get("sample_raw") or st.session_state.get("text_input", "") or ""

# 正規表現でコード領域を抽出する関数
CODE_START = "◆→開始:Pythonコード←◆"
CODE_END = "◆→終了:Pythonコード←◆"
pattern = re.compile(
    re.escape(CODE_START) + r"(.*?)" + re.escape(CODE_END),
    re.DOTALL
)


def split_text_and_code(text: str) -> List[Tuple[str, bool]]:
    parts = []
    last_end = 0
    for m in pattern.finditer(text):
        if m.start() > last_end:
            parts.append((text[last_end:m.start()], False))
        code_inner = m.group(1)
        parts.append((code_inner, True))
        last_end = m.end()
    if last_end < len(text):
        parts.append((text[last_end:], False))
    return parts


def highlight_python_html(code: str, style_name: str = "friendly") -> str:
    lexer = PythonLexer()
    try:
        formatter = HtmlFormatter(noclasses=True, style=style_name)
    except Exception as e:
        fallback_msg = f"<!-- Pygments style '{style_name}' not available: {e}. Falling back to 'default'. -->\n"
        formatter = HtmlFormatter(noclasses=True, style="default")
        return fallback_msg + highlight(code, lexer, formatter)
    return highlight(code, lexer, formatter)


def highlight_python_bbcode(code: str, style_name: str = "friendly") -> str:
    lexer = PythonLexer()
    try:
        formatter = BBCodeFormatter(style=style_name)
    except Exception:
        formatter = BBCodeFormatter(style="default")
    return highlight(code, lexer, formatter)


def remove_black_color_tags_bbcode(text: str) -> str:
    # [color=#000000]...[/color] と [color="#000000"]...[/color] を中身だけ残す
    text = re.sub(r'\[color=#000000\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[color="#000000"\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    return text


def make_html_from_segments(segments: List[Tuple[str, bool]], style_name: str = "friendly") -> str:
    html_parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            code = seg.strip("\n")
            highlighted = highlight_python_html(code, style_name)
            html_parts.append(highlighted)
        else:
            if seg:
                escaped = html.escape(seg)
                escaped = escaped.replace("\n", "<br>\n")
                html_parts.append(f"<div class='plain-text'>{escaped}</div>")
    style_block = """
    <style>
    .streamlit-pygments-output .plain-text {
        background: #ffffff;
        color: #000000;
        padding: 10px;
        border-radius: 6px;
        white-space: pre-wrap;
        margin: 8px 0;
    }
    .streamlit-pygments-output pre { background: #ffffff !important; }
    </style>
    """
    full_html = (
        style_block
        + "<div class='streamlit-pygments-output'>\n"
        + "\n<hr style='opacity:0.1'>\n".join(html_parts)
        + "\n</div>"
    )
    return full_html


def make_bbcode_from_segments(segments: List[Tuple[str, bool]], style_name: str = "friendly") -> str:
    parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            code = seg.strip("\n")
            highlighted_bb = "◆→開始:Pythonコード←◆\n" + remove_black_color_tags_bbcode(highlighted_bb) + "\n◆→終了:Pythonコード←◆"
            highlighted_bb = remove_black_color_tags_bbcode(highlighted_bb)
            parts.append(highlighted_bb)
        else:
            parts.append(seg)
    return "\n\n---\n\n".join(parts)


# 実行ボタン
if st.button("ハイライト実行"):
    if not raw:
        st.warning("まずテキストをアップロードするかコピー＆ペーストしてください。")
    else:
        segments = split_text_and_code(raw)
        if not any(is_code for _, is_code in segments):
            st.info("コードブロックのデリミタが見つかりませんでした。デリミタを確認してください。")
            st.code(raw, language=None)
        else:
            result_html = make_html_from_segments(segments, style)
            st.components.v1.html(
                f"<div>{result_html}</div>",
                height=600,
                scrolling=True,
            )

            if download_html:
                html_file = (
                    "<!doctype html>\n"
                    "<html>\n<head>\n<meta charset='utf-8'>\n"
                    f"<title>Highlighted output</title>\n"
                    "</head>\n<body>\n"
                    f"{result_html}\n"
                    "</body>\n</html>"
                )
                st.download_button(
                    label="結果を HTML としてダウンロード",
                    data=html_file.encode("utf-8"),
                    file_name="highlighted_output.html",
                    mime="text/html",
                )

            if download_txt:
                txt_file = make_bbcode_from_segments(segments, style)
                st.download_button(
                    label="結果を TXT (BBCode) としてダウンロード",
                    data=txt_file.encode("utf-8"),
                    file_name="highlighted_output.txt",
                    mime="text/plain",
                )

# フッタの説明
st.markdown("---")
st.markdown(
    "仕組みの簡単な説明:\n\n"
    "1. テキストを正規表現で `◆→開始:Pythonコード←◆` / `◆→終了:Pythonコード←◆` のペアで分割します。\n"
    "2. コード部分を Pygments (PythonLexer) で HTML または BBCode に変換します。\n"
    "3. 通常テキスト部分は HTML エスケープして改行を <br> に変換し、コード部分と組み合わせて表示します。\n"
)
