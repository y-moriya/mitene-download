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
import logging
import re
from logging import config, getLogger, StreamHandler, Formatter

# メイン設定ファイル読込
with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
    main_config = yaml.safe_load(read_main_config)

url = main_config['mitene_url']
password = main_config['mitene_password']
dl_dir_path = main_config['dl_dir_path']
dl_wait_time = main_config['dl_wait_time']
click_wait_time = main_config['click_wait_time']

# ログ設定ファイル読込
with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
    log_config = yaml.safe_load(read_log_config)

config.dictConfig(log_config)
logger = getLogger('logger')

# 実行時引数からdl_start_dateとdl_end_dateを取得
args = sys.argv
# 引数が2つでない場合はエラーを出力して終了
if len(args) != 3:
    logger.error('引数の数が正しくありません. 2つの引数を指定してください.')
    sys.exit(1)

# 引数が日付形式でない場合はエラーを出力して終了
try:
    dl_start_date = pd.to_datetime(args[1])
    dl_end_date = pd.to_datetime(args[2])
except ValueError:
    logger.error('日付形式が正しくありません. YYYY-MM-DDの形式で入力してください.')
    sys.exit(1)


# ここに設定ファイルのバリデーションを追加したい

tmp_dl_dir_path = os.getcwd()
logger.info('一時ダウンロードフォルダのパス: %s', tmp_dl_dir_path)

# Chromeオプション設定でダウンロード先を変更
chrome_options = Options()

# オプションを適用しヘッドレスモードでChromeを起動
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-gpu')
browser = webdriver.Chrome(options=chrome_options)
browser.implicitly_wait(5)

# オーバーレイ上のボタンをクリックする関数を定義
def click_on_the_overlay(class_name):
    button = browser.find_element(By.CLASS_NAME, class_name)
    time.sleep(click_wait_time)
    browser.execute_script("arguments[0].click();", button)

# 「みてね」のサイトを開く
browser.get(url)
time.sleep(1)

# 現在のURLを取得
cur_url = browser.current_url

# ここにURLが誤っていた場合の処理を入れる

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
    time.sleep(1)
    login_button.click()
    cur_url = browser.current_url

    if cur_url == url:
        logger.info('現在のページのURL: %s', cur_url)
        logger.info('ログインに成功しました.')

else:
    logger.info('現在のページのURL: %s', cur_url)

for page in range(1, 10**4, 1):
    # ページ内のサムネイルの数を数える
    thumbnails = browser.find_elements(By.CLASS_NAME, 'media-img')

    # サムネイルをクリックしてオーバーレイを表示
    click_on_the_overlay('media-img')

    # ページ内の最大撮影日を取得
    max_date_on_page = browser.find_element(By.CLASS_NAME, 'media-took-at').text
    max_date_on_page = pd.to_datetime(max_date_on_page, format='%m/%d/%Y').strftime('%Y-%m-%d')

    # [<]ボタンをクリック
    click_on_the_overlay('prev-button')

    # ページ内の最小撮影日を取得
    min_date_on_page = browser.find_element(By.CLASS_NAME, 'media-took-at').text
    min_date_on_page = pd.to_datetime(min_date_on_page, format='%m/%d/%Y').strftime('%Y-%m-%d')

    # [x]ボタンをクリック
    click_on_the_overlay('close-button')

    logger.info('%sページ目 画像・動画数:%s 撮影日:%sから%s',
                str(page), str(len(thumbnails)),
                min_date_on_page, max_date_on_page)

    # ページ内にダウンロード対象ページがあるか確認
    if dl_start_date > pd.to_datetime(max_date_on_page):
        logger.info('このページ以降の画像・動画は全てDL対象期間外に撮影されたものです.')
        logger.info('処理を終了します.')
        break

    elif pd.to_datetime(min_date_on_page) > dl_end_date:
        logger.info('DL対象期間に撮影された画像・動画はページ内に存在しません.')

    else:
        logger.info('ページ内からDL対象期間に撮影された画像・動画を検索します.')

        # サムネイルをクリックしてオーバーレイを表示
        click_on_the_overlay('media-img')

        for movie in range(1, len(thumbnails) + 1, 1):

            # 撮影日を取得
            shooting_date = browser.find_element(By.CLASS_NAME, 'media-took-at').text

            # shooting_date は 'MM/DD/YYYY' の形式なので 'YYYY-MM-DD' の形式に変換
            shooting_date = pd.to_datetime(shooting_date, format='%m/%d/%Y').strftime('%Y-%m-%d')

            # 撮影日がDL対象であればダウンロード
            if dl_end_date >= pd.to_datetime(shooting_date) >= dl_start_date:
                logger.info('画像・動画%s枚目 撮影日:%s DL対象', str(movie).zfill(2), shooting_date)
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
                            file_name = os.path.split(tmp_file_path)[1]
                            new_file_name = shooting_date + '_' + file_name
                            new_file_path = dl_dir_path + '/' + new_file_name
                            shutil.move(tmp_file_path, new_file_path)
                            time.sleep(5)
                            logger.info('ダウンロード完了. ファイル名: %s', new_file_name)
                            break

                    # 待機時間を過ぎても'.crdownload'以外の拡張子ファイルが確認できない場合は強制処理終了
                    if i >= dl_wait_time:
                        logger.error('タイムアウトしました. DLを中断します.')
                        sys.exit(1)

                    time.sleep(1)

            else:
                logger.info('画像・動画%s枚目 撮影日:%s DL対象外', str(movie).zfill(2), shooting_date)


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
        break
