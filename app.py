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
st.title("テキスト内の Python コードを Pygments でハイライトするツール")
st.markdown(
    "テキスト中のコードは次のデリミタで囲んでください：\n\n"
    "`◆→開始:Pythonコード←◆` と `◆→終了:Pythonコード←◆`"
)

# 入力方法
col1, col2 = st.columns([3, 1])
with col1:
    uploaded = st.file_uploader("テキストファイルをアップロード (省略可)", type=["txt", "md"])
    text_input = st.text_area(
        "またはここにテキストを貼り付けてください（アップロードが優先されます）",
        height=300,
        placeholder="ここにテキストを貼り付け..."
    )
with col2:
    st.markdown("表示スタイル")
    # 利用可能な Pygments スタイルを動的に取得してプルダウンにする
    try:
        styles = sorted(list(get_all_styles()))
    except Exception:
        # まれに取得できない環境向けのフォールバック
        styles = ["friendly", "default", "monokai", "colorful", "autumn"]

    # デフォルトを friendly に（存在しなければ先頭）
    default_index = styles.index("friendly") if "friendly" in styles else 0
    style = st.selectbox("Pygments スタイル", options=styles, index=default_index)

    st.markdown("出力")
    download_html = st.checkbox("ハイライト結果を HTML としてダウンロードする", value=True)
    download_txt = st.checkbox("ハイライト結果を TXT（BBCode）でもダウンロードする", value=False)
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
        # バイナリや別エンコーディングの可能性があるのでリトライ
        raw = uploaded.getvalue().decode("utf-8", errors="replace")
else:
    raw = text_input or ""

# サンプルを表示するオプション
if not raw:
    if st.button("サンプルを読み込む"):
        raw = (
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
        st.experimental_rerun()

# 正規表現でコード領域を抽出する関数
CODE_START = "◆→開始:Pythonコード←◆"
CODE_END = "◆→終了:Pythonコード←◆"
pattern = re.compile(
    re.escape(CODE_START) + r"(.*?)" + re.escape(CODE_END),
    re.DOTALL
)


def split_text_and_code(text: str) -> List[Tuple[str, bool]]:
    """
    テキストを「コードである部分」と「コードでない部分」のリストに分割して返す。
    戻り値は (segment, is_code) のタプルリスト。
    """
    parts = []
    last_end = 0
    for m in pattern.finditer(text):
        # 前の通常テキスト
        if m.start() > last_end:
            parts.append((text[last_end:m.start()], False))
        # コード部分（マッチ内部）
        code_inner = m.group(1)
        parts.append((code_inner, True))
        last_end = m.end()
    # 最後の残り
    if last_end < len(text):
        parts.append((text[last_end:], False))
    return parts


def highlight_python_html(code: str, style_name: str = "friendly") -> str:
    """
    Python コードを Pygments でハイライトして HTML を返す（inline styles を使用）。
    style_name が存在しない等のエラーが起きた場合はフォールバックで 'default' を使い、
    エラーメッセージを HTML コメントとして付加する。
    """
    lexer = PythonLexer()
    try:
        formatter = HtmlFormatter(noclasses=True, style=style_name)
    except Exception as e:
        fallback_msg = f"<!-- Pygments style '{style_name}' not available: {e}. Falling back to 'default'. -->\n"
        formatter = HtmlFormatter(noclasses=True, style="default")
        return fallback_msg + highlight(code, lexer, formatter)
    return highlight(code, lexer, formatter)


def highlight_python_bbcode(code: str, style_name: str = "friendly") -> str:
    """
    Python コードを Pygments の BBCodeFormatter で出力（TXT 用）。
    style_name が使えない場合は 'default' にフォールバック。
    """
    lexer = PythonLexer()
    try:
        formatter = BBCodeFormatter(style=style_name)
    except Exception:
        formatter = BBCodeFormatter(style="default")
    return highlight(code, lexer, formatter)


def remove_black_color_tags_bbcode(text: str) -> str:
    """
    BBCode 出力中の [color=#000000]...[/color] と [color=\"#000000\"]...[/color] を
    見つけた場合のみタグを削除して中身だけ返す。
    """
    # 2 通りの表記に対応
    text = re.sub(r'\[color=#000000\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\[color="#000000"\](.*?)\[/color\]', r'\1', text, flags=re.DOTALL)
    return text


def make_html_from_segments(segments: List[Tuple[str, bool]], style_name: str = "friendly") -> str:
    """
    セグメントのリスト（(text, is_code)）から最終 HTML を組み立てる。
    通常テキストは HTML エスケープして改行を <br> に変換する。
    コードは Pygments の HTML をそのまま埋め込む。
    また、plain-text 部分は白背景 + 黒文字にして、ダークテーマ（システム依存）でも読めるようにしています。
    """
    html_parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            # 先頭と末尾の不要な改行をトリム
            code = seg.strip("\n")
            highlighted = highlight_python_html(code, style_name)
            html_parts.append(highlighted)
        else:
            if seg:
                escaped = html.escape(seg)
                escaped = escaped.replace("\n", "<br>\n")
                # 常に plain-text 部分は白背景・黒文字にする（コード部分は Pygments が白背景を付与している）
                html_parts.append(f"<div class='plain-text'>{escaped}</div>")
    # 最小のスタイル（plain-text を白背景に固定）
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
    /* Pygments の inline-style でコードは既に見た目がつくので追記は最小限 */
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
    """
    セグメントを結合して TXT/BBCode 出力文字列を作成する。
    - 通常テキストはそのまま（元のプレーンテキスト）
    - コード部は BBCodeFormatter によるカラー化を適用
    - BBCode の [color=#000000]...[/color] は中身だけ残してタグは削除
    """
    parts: List[str] = []
    for seg, is_code in segments:
        if is_code:
            code = seg.strip("\n")
            highlighted_bb = highlight_python_bbcode(code, style_name)
            # 指定通り、黒色タグは削除して中身だけにする
            highlighted_bb = remove_black_color_tags_bbcode(highlighted_bb)
            parts.append(highlighted_bb)
        else:
            # 非コードはそのまま（末尾に改行が必要なら保持）
            parts.append(seg)
    # 適度に区切る（HTML 側と見た目を揃えるため改行で区切る）
    return "\n\n".join(parts)


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
            # Streamlit に HTML を埋め込む（unsafe_allow_html 相当を使う）
            st.components.v1.html(
                f"<div>{result_html}</div>",
                height=600,
                scrolling=True,
            )

            # HTML ダウンロード（オプション）
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

            # TXT (BBCode) ダウンロード（オプション）
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
    "4. plain-text 部分は常に白背景／黒文字にして、ダークテーマでも読みやすくしています。\n"
)
