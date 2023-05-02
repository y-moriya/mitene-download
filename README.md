forked from https://github.com/OGAWASanshiro/mitene-download

# mitene-download refined

[みてね](https://mitene.us/)ブラウザ版から写真・動画ファイルを自動でダウンロードできるプログラムです。<br>
写真・動画の撮影日を指定してダウンロードすることができます。

## オリジナルからの変更点

- 撮影日の指定を `main_config.yml` から実行時引数に変更
  - 最後にダウンロードを指定した日付が `last_downloaded_date.txt` に保存される
  - 次回、引数なしで実行すると最後の日付から今日までを対象の日付としてダウンロードを実行します
- `main_config.yml` を gitignore しているため `main_config.sample.yml` をリネームして設定してください
- WSL2 Ubuntu 22.04 環境でのみ動作確認済み
- Selenium のダウンロードディレクトリがカレントディレクトリから変更できなかったため（原因はわかってない）、以下の手順で実行すること

```bash
$ mkdir tmp_dl_dir
$ cd tmp_dl_dir
$ python3 ../mitene_download.py YYYY-MM-DD YYYY-MM-DD
```

- `pip3 install -r requirements.txt` で必要なライブラリがインストールされます
- ダウンロードしたファイル名を `日付_MD5HASH.ext` に変更し、同一ファイルがある場合は一時ファイルをそのまま削除するようにした
  - ファイル名に含まれるほか、ダウンロードフォルダに `hash_list.txt` として保存されます
  - `list_hash.py` を実行するとすでにダウンロード済みのファイルに対して全て再計算されます
