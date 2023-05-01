forked from https://github.com/OGAWASanshiro/mitene-download

# mitene-download refined

[みてね](https://mitene.us/)ブラウザ版から写真・動画ファイルを自動でダウンロードできるプログラムです。<br>
写真・動画の撮影日を指定してダウンロードすることができます。

## オリジナルからの変更点

- 撮影日の指定を `main_config.yml` から実行時引数に変更
- `main_config.yml` を gitignore しているため `main_config.sample.yml` をリネームして設定してください
- WSL2 Ubuntu 22.04 環境でのみ動作確認済み
- Selenium のダウンロードディレクトリがカレントディレクトリから変更できなかったため（原因はわかってない）、以下の手順で実行すること

```bash
$ mkdir tmp_dl_dir
$ cd tmp_dl_dir
$ python3 ../mitene_download.py YYYY-MM-DD YYYY-MM-DD
```

- `pip3 install -r requirements.txt` で必要なライブラリがインストールされます
