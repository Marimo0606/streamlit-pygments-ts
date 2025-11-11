# streamlit-pygments-ts

これは Streamlit Community Cloud 上で動かす、アップロードされたテキスト中の特定のコード部分を Pygments（pygmentize）でハイライトして HTML にするツールのサンプル実装です。

特徴:
- テキスト中のコードブロックは以下のようなデリミタで囲まれていると仮定します:
  - 開始: `◆→開始:Pythonコード←◆`
  - 終了: `◆→終了:Pythonコード←◆`
- 上記デリミタで囲まれた部分だけを Python コードとして Pygments でハイライトします。
- ハイライトスタイル（Pygments style）はアプリのプルダウンで選択できます。アプリはシステムにインストールされている全ての Pygments スタイルを列挙するため、サードパーティ製のスタイルもインストールすれば候補に表示されます。
- 例として kmuto/pygments-style-texlistings を requirements.txt に追加してあり、Streamlit Community Cloud にデプロイすると候補に現れます。
- ハイライトは inline style（noclasses=True）で出力するため、Streamlit のコンポーネント内にそのまま埋め込んで表示できます。
- 処理後の HTML をダウンロードできます。

使い方（簡潔）:
1. このリポジトリを GitHub に push します。
2. Streamlit Community Cloud に GitHub リポジトリを接続してデプロイします。Streamlit は `streamlit_app.py` を探して起動します。
3. ブラウザでアプリを開き、テキストファイルをアップロードするかテキストを貼り付けて「ハイライト実行」を押します。
