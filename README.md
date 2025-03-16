# KCD Alternative Japanese Translation - Czech based transcription

KCD1, 2 の固有名詞を現地語準拠にしたり, 各種誤訳等を修正したりする


TODO: 未変更箇所もまとめて配布するのは良くないと思う.

## ユーザー向け

Releases から最新のものをダウンロードしてください.

## 自分で使いたい人向け

単純な変換でだいたいなんとかなると思って作ったが, 予想より面倒な問題だった. この変換でできることは限られており, 必ず出力に対して手動の確認が必要になる. LLMとかのファジーな方法を使ったほうが効率良かったかも知れない. 



### 使い方

変換ツールをPythonで作っているため, python環境を構築する知識が必要になる. Python 3.12 で作業している. 環境設定はPoetryでやっている.


以下のようなフォルダ配置を想定している.

* {KCD1}
  * private/
    * Czech_xml
    * {Japanese_xml}
  * dicts
  * dicts-id
  * dicts-rev
  * output
* {KCD2}
  * private
    * Czech_xml
    * {Japanese_xml}
  * dicts
  * dicts-id
  * dicts-rev
  * output

`{}` 内の名称は変更しても良い. `Czech_xml`, `{Japanese_xml}` には, 本体の Czech_xml.pak, Japense_xml.pak を展開して出てきたXMLファイルを配置する. `dicts*` には, 単語やID単位で置換するテキストの一覧を書いたファイルを配置する.

KCD1フォルダに対して, XMLファイル内の訳文を置換したい場合は以下を実行する.

```
python reader.py KCD1
```

Japanese_xml 以外のフォルダを指定したい場合は, `--dir-lang` オプションがある.

出力は output フォルダに書き込まれる.

CSVファイルはそれぞれ, 以下のような列にする.

dicts-id フォルダは, 少なくとも以下の列を持つ必要がある.

* id: str
* text_EN: str
* text_CZ: str
* text: str or blank
* modified: str
* onlyid

text 列は, 変換対象の言語の, オリジナルのテキストを与え, modified 列には, 変換後の文字列を指定する.

dicts, dicts-rev は, 以下のような列を持つ必要がある

* text_EN
* text
* modified

これらはIDの一致判定を行わないため, ID列は不要であるし, ID列があっても読み込まない.

### 処理の詳細

この処理は以下のような内容になる

1. dicts-id 内のCSVファイルを読み込み, IDの一致したエントリに対して, テキストを置き換える. ここでIDが一致したエントリは, **以降の置換処理が適用されない**.
2. dicts-id 内のCSVファイルを読み込み, onlyid フラグのついた列と, dicts 内のCSVファイルを読み込んだ単語変換表を使い, 単語の単純一致で置換を行う. 正規表現は想定されていない.
3. ricts-rev 内のCSVファイルを読み込み, 単語の単純で置換を行う.  正規表現は想定されていない.

処理 (2) が単純一致なので, 誤検知がそれなりにある. 誤検知によって発生した問題のある文字列をやはり再変換で修正するのが処理(3)の意図である.

### PAKファイルへの再変換

KCDのPAKファイルは実質ZIPのはずだが, 特殊なパラメータ設定がされているらしい. 1ではWinRARで圧縮したときだけ認識された. 2ではそれも使えなくなったが, 要求される設定で圧縮する専用ツールを作成したModderがいる.

https://www.nexusmods.com/kingdomcomedeliverance2/mods/78