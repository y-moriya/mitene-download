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

## newsfeeds_download.py

近況ページから画像をダウンロードします。すでにダウンロード済みの近況ページはスキップされます。

Usage

```bash
$ cd tmp_dl_dir
$ python3 ../newsfeeds_download.py
```

`--all` オプションを付けると `もっと見る` をクリックして全ての近況について処理を行います。

## upload.py

- DL済みの画像をまとめて Google Photos にアップロードし、アップロード後にローカルからは画像を削除します。
  - 動画は何もしません。
- Google Cloud Console でプロジェクトを作成し、Photos Library API の有効化、「デスクトップクライアント」の認証情報を作成し、`client_secrets.json` をダウンロードして root に配置してください。
-  `main_config.yml` の `upload_album_name` にアップロード先のアルバムを指定してください。
   -  アルバムが存在しない場合は自動で作成されます。
   -  このスクリプトから作成したアルバムでないとアップロードができないので注意してください。
- 動画ファイルは `main_config.yml` の `video_move_path` に移動します。

Usage

```bash
$ cd tmp_dl_dir
$ python3 ../upload.py
```
