import re
import html
from typing import List, Tuple

import streamlit as st
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter, BBCodeFormatter
from pygments.styles import get_all_styles

# ------------------ ページ設定 ------------------
st.set_page_config(page_title="Pygments ハイライト (Streamlit)", layout="wide")

# ------------------ グローバルCSS（外側の余白を詰める） ------------------
st.markdown("""
<style>
/* 全体の縦リズム（ウィジェット間のギャップ） */
section.main > div.block-container div[data-testid="stVerticalBlock"]{
  gap: .5rem !important;              /* さらに詰めたい → .4rem や .35rem */
  padding-top: 0 !important;
}

/* TextArea 周り（ボタン前のアキを詰める） */
section.main div[data-testid^="stTextArea"]{
  margin-top: .25rem !important;
  margin-bottom: .5rem !important;
}
section.main div[data-testid^="stTextArea"] textarea{
  min-height: 12rem !important;       /* 10〜12rem 推奨 */
  line-height: 1.6 !important;
}
section.main div[data-testid^="stTextArea"] textarea:placeholder-shown{
  overflow-y: hidden !important;       /* 未入力時は縦スクロール非表示 */
}

/* ファイルアップローダ & ラベル */
section.main div[data-testid="stFileUploader"]{ margin-bottom: .5rem !important; }
section.main div[data-testid="stWidgetLabel"]{ margin-bottom: .25rem !important; }

/* ボタン上下の余白を抑える */
section.main div[data-testid="stButton"]{
  margin-top: .25rem !important;
  margin-bottom: .5rem !important;
}
section.main .stButton > button{
  padding-top: .4rem !important;
  padding-bottom: .4rem !important;
}

/* ボタン直後のブロック（結果表示など）の頭をさらに詰める */
section.main div[data-testid="stButton"] + div[data-testid="stVerticalBlock"]{
  margin-top: 0 !important;
  padding-top: 0 !important;
}

/* Markdown 段落・見出しの余白をほどよくタイトに */
section.main div[data-testid="stMarkdownContainer"] p{ margin: .2rem 0 .6rem 0 !important; }
section.main .block-container h2, 
section.main .block-container h3{ margin: .2rem 0 .6rem 0 !important; }
</style>
""", unsafe_allow_html=True)

# ------------------ ヘッダ ------------------
st.title("テキスト内のPythonコードをPygmentsでハイライト")
st.markdown(
    """### サンプルテキスト（コピーして使えます）

次のように、デリミタで囲んだ部分がPythonコードとして認識されます。

```
これはサンプルのテキストです。

◆→開始:Pythonコード←◆
def hello(name):
print(f"Hello, {name}!")

for i in range(3):
hello('world')
◆→終了:Pythonコード←◆

普通の文章に戻ります。
```
"""
)

# ------------------ 入力UI ------------------
col1, col2 = st.columns([3, 1])
with col1:
    uploaded = st.file_uploader("テキストファイルをアップロード (省略可)", type=["txt"])
    text_input = st.text_area(
        "またはここにテキストを貼り付けてください（アップロードが優先されます）。「ハイライト実行」をクリックすると色を確認できます",
        height=300,
        placeholder="ここにテキストを貼り付け..."
    )
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
    download_txt = st.checkbox("ハイライト結果を .txt（BBCode）としてダウンロードする", value=True)
    st.markdown("---")
    st.markdown("注意")
    st.caption(
        "サードパーティ製のスタイル（例: kmuto/pygments-style-texlistings）を使いたい場合は "
        "requirements.txt にそのパッケージを追加してから Streamlit Community Cloud にデプロイしてください。"
    )

# ------------------ 入力ソース決定 ------------------
if uploaded is not None:
    try:
        raw = uploaded.read().decode("utf-8")
    except Exception:
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
else:
    raw = text_input or ""

# ------------------ 解析のための定義 ------------------
CODE_START = "◆→開始:Pythonコード←◆"
CODE_END = "◆→終了:Pythonコード←◆"
pattern = re.compile(re.escape(CODE_START) + r"(.*?)" + re.escape(CODE_END), re.DOTALL)

def split_text_and_code(text: str) -> List[Tuple[str, bool]]:
    parts = []
    last_end = 0
    for m in pattern.finditer(text):
        if m.start() > last_end:
            parts.append((text[last_end:m.start()], False))
        parts.append((m.group(1), True))
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
    text = re.sub(r'\[color=#000000\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[color="#000000"\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    return text

def make_html_from_segments(segments: List[Tuple[str, bool]], style_name: str = "friendly") -> str:
    html_parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            code = seg.strip("\n")
            html_parts.append(highlight_python_html(code, style_name))
        else:
            if seg:
                escaped = html.escape(seg).replace("\n", "<br>\n")
                html_parts.append(f"<div class='plain-text'>{escaped}</div>")

    # iframe内（結果側）の余白最小化CSS
    style_block = """
<style>
.streamlit-pygments-output{ margin:0; padding:0; }
/* プレーンテキスト */
.streamlit-pygments-output .plain-text{
    background:#fff; color:#000; padding:6px; border-radius:6px;
    white-space:pre-wrap; margin:4px 0; line-height:1.5;
}
/* Pygments 出力（div.highlight > pre） */
.streamlit-pygments-output .highlight{ margin:0 !important; }
.streamlit-pygments-output .highlight pre{
    margin:4px 0 !important; background:#fff !important; line-height:1.5;
}
/* 先頭・末尾の余白カット */
.streamlit-pygments-output > :first-child{ margin-top:0 !important; }
.streamlit-pygments-output > :last-child{  margin-bottom:0 !important; }
</style>
"""
    full_html = (
        style_block
        + "<div class='streamlit-pygments-output'>\n"
        + "\n".join(html_parts)  # 区切り線(hr)は入れない
        + "\n</div>"
    )
    return full_html

def make_bbcode_from_segments(segments: List[Tuple[str, bool]], style_name: str = "friendly") -> str:
    parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            code = seg.strip("\n")
            highlighted_bb = highlight_python_bbcode(code, style_name)
            highlighted_bb = "◆→開始:Pythonコード←◆\n" + remove_black_color_tags_bbcode(highlighted_bb) + "\n◆→終了:Pythonコード←◆"
            parts.append(highlighted_bb)
        else:
            parts.append(seg)
    return "\n".join(parts)

# ------------------ 実行と出力 ------------------
# ラッパーで囲ってこの領域だけ縦ギャップをさらに詰める
st.markdown('<div class="tight">', unsafe_allow_html=True)

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
            st.components.v1.html(f"<div>{result_html}</div>", height=600, scrolling=True)

            if download_html:
                html_file = (
                    "<!doctype html>\n<html>\n<head>\n<meta charset='utf-8'>\n"
                    "<title>Highlighted output</title>\n</head>\n<body>\n"
                    f"{result_html}\n</body>\n</html>"
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

st.markdown('</div>', unsafe_allow_html=True)

# この領域だけさらにタイトに（外側の最終上書き）
st.markdown("""
<style>
.tight [data-testid="stVerticalBlock"]{ gap:.35rem !important; padding-top:0 !important; }
.tight [data-testid="stButton"]{ margin-top:.2rem !important; margin-bottom:.35rem !important; }
.tight [data-testid="stComponent"]{ margin-top:.2rem !important; margin-bottom:.4rem !important; }
.tight [data-testid="stDownloadButton"]{ margin:.3rem 0 !important; }
.tight [data-testid="stMarkdownContainer"] p, .tight h2, .tight h3{
    margin-top:.2rem !important; margin-bottom:.5rem !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------ フッタ ------------------
st.markdown("---")
st.markdown(
    "仕組みの簡単な説明:\n\n"
    "1. テキストを正規表現で `◆→開始:Pythonコード←◆` / `◆→終了:Pythonコード←◆` のペアで分割します。\n"
    "2. コード部分を Pygments (PythonLexer) で HTML または BBCode に変換します。\n"
    "3. 通常テキスト部分は HTML エスケープして改行を <br> に変換し、コード部分と組み合わせて表示します。\n"
)
