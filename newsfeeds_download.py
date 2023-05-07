#!/usr/bin/env python
# coding: utf-8

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import sys
import shutil
import time
import glob
import pandas as pd
import yaml
import hashlib
import re
from logging import config, getLogger

# メイン設定ファイル読込
with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
    main_config = yaml.safe_load(read_main_config)

url = main_config['mitene_url']
password = main_config['mitene_password']
dl_dir_path = main_config['dl_dir_path']
dl_wait_time = main_config['dl_wait_time']
click_wait_time = main_config['click_wait_time']
last_downloaded_date_file = main_config['last_downloaded']

# ログ設定ファイル読込
with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
    log_config = yaml.safe_load(read_log_config)

config.dictConfig(log_config)
logger = getLogger('logger')

download_all_flag = False
# 引数を取得
args = sys.argv
if len(args) == 2:
    download_all_flag = args[1] == '--all'

tmp_dl_dir_path = os.getcwd()
logger.info('一時ダウンロードフォルダのパス: %s', tmp_dl_dir_path)

# Chromeオプションを適用しヘッドレスモードでChromeを起動
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
browser = webdriver.Chrome(options=chrome_options)
browser.implicitly_wait(5)

# オーバーレイ上のボタンをクリックする関数を定義
def click_on_the_overlay(class_name):
    button = browser.find_element(By.CLASS_NAME, class_name)
    time.sleep(click_wait_time)
    browser.execute_script("arguments[0].click();", button)

# ダウンロード済みの最新のニュースフィードIDを取得
if not os.path.exists(dl_dir_path + '/newsfeed_id_list.txt'):
    # ファイルが存在しない場合は作成する
    with open(dl_dir_path + '/newsfeed_id_list.txt', 'w') as f:
        f.write('')
    logger.info('newsfeed_id_list.txt を作成しました.')

with open(dl_dir_path + '/newsfeed_id_list.txt', 'r') as f:
    newsfeed_id_list = f.read().splitlines()

# 「みてね」のサイトを開く
browser.get(url)
browser.implicitly_wait(5)

# 現在のURLを取得
cur_url = browser.current_url

# 現在のページがログインページの場合はパスワードを入力してログイン
if cur_url.endswith(('login', 'login/')):
    logger.info('現在のページのURL: %s', cur_url)
    logger.info('ログインします.')

    # パスワードを入力
    element = browser.find_element(By.ID, 'session_password')
    element.clear()
    element.send_keys(password)

    # ログインボタンをクリック
    login_button = browser.find_element(By.NAME, 'commit')
    browser.implicitly_wait(5)
    login_button.click()
    cur_url = browser.current_url

    if cur_url == url:
        logger.info('現在のページのURL: %s', cur_url)
        logger.info('ログインに成功しました.')

else:
    logger.info('現在のページのURL: %s', cur_url)

# 近況ページ newsfeeds を開く
browser.get(url + '/newsfeeds')
browser.implicitly_wait(5)
cur_url = browser.current_url
logger.info('現在のページのURL: %s', cur_url)

# 全てをダウンロードするフラグが立っている場合は「もっと見る」ボタンをクリック
if download_all_flag:
    # 「もっと見る」ボタンを取得
    element = browser.find_element(By.CLASS_NAME, 'newsfeed-more-link')
    while element:
        browser.implicitly_wait(5)
        if element.text == 'See More':
            click_on_the_overlay('newsfeed-more-link')
            element = browser.find_element(By.CLASS_NAME, 'newsfeed-more-link')
        else:
            break

# 指定されたパターンに一致する要素を取得
pattern = re.compile(r"\d+ new photos?/videos? have been added.")
matching_hrefs = []
target_newsfeed_ids = []

for p_element in browser.find_elements(By.TAG_NAME, "p"):
    if pattern.match(p_element.text):
        # parent の a タグの href 属性を取得
        parent_element = p_element.find_element(By.XPATH, '../../../..')
        href = parent_element.get_attribute('href')
        matching_hrefs.append(href)

        # r'newsfeeds/(\d+)' に一致する文字列を取得
        match = re.search(r'newsfeeds/(\d+)', href)
        if match:
            # \d+ 部分を取得
            newsfeed_id = match.group(1)
            if newsfeed_id in newsfeed_id_list:
                logger.info('newsfeed_id: %s はダウンロード済みです.', newsfeed_id)
                continue
            else:
                target_newsfeed_ids.append(newsfeed_id)

        else:
            logger.info('newsfeed_id が存在しないためスキップします.')
            continue

if target_newsfeed_ids:
    for newsfeed_id in target_newsfeed_ids:
        href = url + '/newsfeeds/' + newsfeed_id
        browser.get(href)

        logger.info('newsfeed_id: %s をダウンロードします.', newsfeed_id)
        logger.info('ページ内から画像・動画を検索します.')
        # ページ内のサムネイルの数を数える
        thumbnails = browser.find_elements(By.CLASS_NAME, 'media-img')

        # サムネイルをクリックしてオーバーレイを表示
        click_on_the_overlay('media-img')

        for movie in range(1, len(thumbnails) + 1, 1):
            # 撮影日を取得
            shooting_date = browser.find_element(By.CLASS_NAME, 'media-took-at').text
            # shooting_date は 'MM/DD/YYYY' の形式なので 'YYYY-MM-DD' の形式に変換
            shooting_date = pd.to_datetime(shooting_date, format='%m/%d/%Y').strftime('%Y-%m-%d')
            logger.info('ダウンロードを開始します.')

            # [ダウンロード]ボタンをクリック
            click_on_the_overlay('download-button')

            # 1秒毎にダウンロード状況を判定
            for i in range(dl_wait_time + 1):

                # ダウンロードフォルダ内のファイル一覧を取得
                download_files = glob.glob(tmp_dl_dir_path + '/' +'*.*')

                if i != 0 and i % 30 == 0:
                    logger.debug(str(i) + '秒経過')

                # ファイルが存在する場合
                if download_files:

                    # 拡張子を抽出
                    extension = os.path.splitext(download_files[0])

                    # 拡張子が '.crdownload' でなければダウンロード完了、待機を抜ける
                    if '.crdownload' not in extension[1]:
                        tmp_file_path = glob.glob(tmp_dl_dir_path + "/" +"*.*")[0]
                        # ファイルのハッシュを取得
                        file_hash = hashlib.md5(open(tmp_file_path, 'rb').read()).hexdigest()
                        # ダウンロードフォルダにあるhash_list.txtを読み込む
                        with open(dl_dir_path + '/hash_list.txt', 'r') as f:
                            hash_list = f.read().splitlines()
                        # ハッシュリストにハッシュが存在する場合はダウンロードしたファイルを削除する
                        if file_hash in hash_list:
                            logger.info('既存ファイルが存在するため、一時保存フォルダから削除します. ハッシュ: %s', file_hash)
                            os.remove(tmp_file_path)
                            time.sleep(5)
                            break
                        # ハッシュリストにハッシュが存在しない場合はハッシュリストに追加し、ファイルを移動する
                        else:
                            with open(dl_dir_path + '/hash_list.txt', 'a') as f:
                                f.write(file_hash + '\n')

                            new_file_name = shooting_date + '_' + file_hash + extension[1]
                            new_file_path = dl_dir_path + '/' + new_file_name
                            shutil.move(tmp_file_path, new_file_path)
                            logger.info('ダウンロード完了. ファイル名: %s', new_file_name)
                            time.sleep(5)
                            break

                # 待機時間を過ぎても'.crdownload'以外の拡張子ファイルが確認できない場合は強制処理終了
                if i >= dl_wait_time:
                    logger.error('タイムアウトしました. DLを中断します.')
                    sys.exit(1)

                time.sleep(1)
            movie += 1

            # [>]ボタンをクリック
            click_on_the_overlay('next-button')

        # [x]ボタンをクリック
        click_on_the_overlay('close-button')

        # [次へ]ボタンが有効か無効か判定
        next_btn = browser.find_element(By.CLASS_NAME, 'next')
        next_btn_tag_a = next_btn.find_element(By.TAG_NAME, 'a')
        next_btn_tag_a_attr_value = next_btn_tag_a.get_attribute("class")

        # 有効なら[次へ]ボタンをクリック
        if next_btn_tag_a_attr_value == 'follower-paging-next-link':
            logger.info('次のページに遷移します.')
            next_button = browser.find_element(By.CLASS_NAME, 'follower-paging-next-link')
            next_button.click()
            time.sleep(1)

        #無効なら処理終了
        else:
            logger.info('このページが最終ページです.')
            logger.info('処理を終了します.')
            # 処理が完了したIDをリストに追加
            with open(dl_dir_path + '/newsfeed_id_list.txt', 'a') as f:
                f.write(newsfeed_id + '\n')
            continue

# ブラウザを閉じる
browser.close()
browser.quit()

logger.info('処理が完了しました.')
sys.exit(0)
