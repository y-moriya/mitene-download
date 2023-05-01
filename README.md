forked from https://github.com/OGAWASanshiro/mitene-download

# mitene-download
[みてね](https://mitene.us/)ブラウザ版から写真・動画ファイルを自動でダウンロードできるプログラムです。<br>
写真・動画の撮影日を指定してダウンロードすることができます。

## 検証環境
以下の環境で検証を行なっています。
- macOS Catalina バージョン 10.15.7
- Python バージョン 3.9.7
- Google Chrome バージョン 100.0.4896.127

### 使用したPythonモジュール、ライブラリ
- os
- sys
- time
- glob
- shutil
- selenium: ChromeDriverを使い、みてねブラウザ版を操作します
- pandas: datetime型データの比較などに使用
- yaml: .yml形式の設定ファイルを読み込みます
- logging: ログの出力を行います

## 使い方
1. ディレクトリを作成し、 `mitene_download.py` と2つの設定ファイルを下記のように配置してください。
```
例）
mitene-download
├── mitene_download.py
├── main_config.yml
└── log_config.yml
```
2. 写真・動画のダウンロード先となるディレクトリを作成し、絶対パスを確認します。
```
例）
/Users/OGAWA_Sanshiro/Desktop/DLフォルダ
```
3. `main_config.yml` を開き設定を記述します。
```
例）
mitene_url: 'https://mitene.us/xxxx' # みてねのURL
mitene_password: 'xxxxxxxx' # みてねのパスワード
dl_dir_path: '/Users/OGAWA_Sanshiro/Desktop/DLフォルダ' # 2で作成したディレクトリの絶対パス
dl_start_date: 2022-01-01 # DLしたい写真・動画の撮影日の始まり（yyyy-mm-dd形式）
dl_end_date: 2022-01-07 # DLしたい写真・動画の撮影日の終わり（yyyy-mm-dd形式）
dl_wait_time: 300 # DL時のタイムアウト設定（秒数）
```
4. ターミナルから `mitene-download.py` を実行してください。
```
例）
$ cd mitene-download
```
```
$ python mitene_download.py
```

## 注意点、要改善点
- 読み込んだ設定ファイルのバリデーションを追加する必要がある。
- DL対象ファイルが数十に及ぶとChromeがメモリを消費しすぎて落ちてしまい、強制終了となる。<br>
これを回避するにはChromeを意図的に落とす→再度立ち上げるというプログラムを行う必要がある。
