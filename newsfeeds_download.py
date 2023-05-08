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

# オーバーレイ上のボタンをクリックする関数
def click_on_the_overlay(class_name):
    button = browser.find_element(By.CLASS_NAME, class_name)
    time.sleep(click_wait_time)
    browser.execute_script("arguments[0].click();", button)

# 撮影日を取得する
def get_shooting_date():
    # 撮影日を取得
    shooting_date = browser.find_element(By.CLASS_NAME, 'media-took-at').text
    # shooting_date は 'MM/DD/YYYY' の形式なので 'YYYY-MM-DD' の形式に変換
    shooting_date = pd.to_datetime(shooting_date, format='%m/%d/%Y').strftime('%Y-%m-%d')
    return shooting_date

# [次へ]ボタンが有効か無効かを判定する
def is_next_button_enabled():
    next_btn = browser.find_element(By.CLASS_NAME, 'next')
    next_btn_tag_a = next_btn.find_element(By.TAG_NAME, 'a')
    next_btn_tag_a_attr_value = next_btn_tag_a.get_attribute("class")
    return next_btn_tag_a_attr_value == 'follower-paging-next-link'

# ダウンロードされたファイルを処理する
def process_downloaded_file(tmp_file_path, dl_dir_path, shooting_date):
    file_hash = hashlib.md5(open(tmp_file_path, 'rb').read()).hexdigest()

    with open(dl_dir_path + '/hash_list.txt', 'r') as f:
        hash_list = f.read().splitlines()

    if file_hash in hash_list:
        logger.info('既存ファイルが存在するため、一時保存フォルダから削除します. ハッシュ: %s', file_hash)
        os.remove(tmp_file_path)
    else:
        with open(dl_dir_path + '/hash_list.txt', 'a') as f:
            f.write(file_hash + '\n')

        extension = os.path.splitext(tmp_file_path)[1]
        new_file_name = shooting_date + '_' + file_hash + extension
        new_file_path = dl_dir_path + '/' + new_file_name
        shutil.move(tmp_file_path, new_file_path)
        logger.info('ダウンロード完了. ファイル名: %s', new_file_name)

    time.sleep(5)

# ダウンロードを待機しつつファイルを処理する
def download_and_process_file(tmp_dl_dir_path, dl_dir_path, dl_wait_time):
    shooting_date = get_shooting_date()
    logger.info('ダウンロードを開始します.')

    click_on_the_overlay('download-button')

    for i in range(dl_wait_time + 1):
        if i != 0 and i % 30 == 0:
            logger.debug(str(i) + '秒経過')

        download_files = glob.glob(tmp_dl_dir_path + '/' + '*.*')

        if download_files:
            tmp_file_path = download_files[0]
            extension = os.path.splitext(tmp_file_path)[1]

            if '.crdownload' not in extension:
                process_downloaded_file(tmp_file_path, dl_dir_path, shooting_date)
                break

        if i >= dl_wait_time:
            logger.error('タイムアウトしました. DLを中断します.')
            sys.exit(1)

        time.sleep(1)

    click_on_the_overlay('next-button')

# 全てをダウンロードするかどうか
def is_download_all():
    # 引数を取得
    args = sys.argv
    if len(args) == 2:
        return args[1] == '--all'
    return False

# See More をクリックする
def click_see_more():
    # 「もっと見る」ボタンを取得
    element = browser.find_element(By.CLASS_NAME, 'newsfeed-more-link')
    while element:
        browser.implicitly_wait(5)
        if element.text == 'See More':
            click_on_the_overlay('newsfeed-more-link')
            element = browser.find_element(By.CLASS_NAME, 'newsfeed-more-link')
        else:
            return

def login(url, password):
    cur_url = browser.current_url
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

def get_target_newsfeed_ids(dl_dir_path):
    # ダウンロード済みの最新のニュースフィードIDを取得
    if not os.path.exists(dl_dir_path + '/newsfeed_id_list.txt'):
        # ファイルが存在しない場合は作成する
        with open(dl_dir_path + '/newsfeed_id_list.txt', 'w') as f:
            f.write('')
        logger.info('newsfeed_id_list.txt を作成しました.')

    with open(dl_dir_path + '/newsfeed_id_list.txt', 'r') as f:
        newsfeed_id_list = f.read().splitlines()

    photos_pattern = re.compile(r"\d+ new photos?/videos? have been added.")
    target_newsfeed_ids = []
    for p_element in browser.find_elements(By.TAG_NAME, "p"):
        if photos_pattern.match(p_element.text):
            # parent の a タグの href 属性を取得
            parent_element = p_element.find_element(By.XPATH, '../../../..')
            href = parent_element.get_attribute('href')

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
    return target_newsfeed_ids

def process_newsfeed(url, newsfeed_id, tmp_dl_dir_path, dl_dir_path, dl_wait_time):
    browser.get(url + '/newsfeeds/' + newsfeed_id)

    logger.info('newsfeed_id: %s をダウンロードします.', newsfeed_id)
    logger.info('ページ内から画像・動画を検索します.')

    thumbnails = browser.find_elements(By.CLASS_NAME, 'media-img')
    click_on_the_overlay('media-img')

    for _ in range(len(thumbnails)):
        download_and_process_file(tmp_dl_dir_path, dl_dir_path, dl_wait_time)

    click_on_the_overlay('close-button')

    if is_next_button_enabled():
        logger.info('次のページに遷移します.')
        next_button = browser.find_element(By.CLASS_NAME, 'follower-paging-next-link')
        next_button.click()
        time.sleep(1)
    else:
        logger.info('このページが最終ページです.')
        logger.info('処理を終了します.')
        with open(dl_dir_path + '/newsfeed_id_list.txt', 'a') as f:
            f.write(newsfeed_id + '\n')

def main(main_config):
    url = main_config['mitene_url']
    password = main_config['mitene_password']
    dl_dir_path = main_config['dl_dir_path']
    dl_wait_time = main_config['dl_wait_time']

    tmp_dl_dir_path = os.getcwd()
    logger.info('一時ダウンロードフォルダのパス: %s', tmp_dl_dir_path)

    # 「みてね」のサイトを開く
    browser.get(url)
    browser.implicitly_wait(5)

    # 現在のURLを取得
    cur_url = browser.current_url

    # 現在のページがログインページの場合はパスワードを入力してログイン
    if cur_url.endswith(('login', 'login/')):
        login(url, password)
    else:
        logger.info('現在のページのURL: %s', cur_url)

    # 近況ページ newsfeeds を開く
    browser.get(url + '/newsfeeds')
    browser.implicitly_wait(5)

    # 全てをダウンロードするフラグが立っている場合は「もっと見る」ボタンが消えるまでクリック
    if is_download_all():
        click_see_more()

    # ダウンロード対象のニュースフィードIDを取得
    target_newsfeed_ids = get_target_newsfeed_ids(dl_dir_path)

    if target_newsfeed_ids:
        for newsfeed_id in target_newsfeed_ids:
            process_newsfeed(url, newsfeed_id, tmp_dl_dir_path, dl_dir_path, dl_wait_time)

# 実行
if __name__ == '__main__':

    # メイン設定ファイル読込
    with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
        main_config = yaml.safe_load(read_main_config)
    click_wait_time = main_config['click_wait_time']

    # ログ設定ファイル読込
    with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
        log_config = yaml.safe_load(read_log_config)

    config.dictConfig(log_config)
    logger = getLogger('logger')

    # Chromeオプションを適用しヘッドレスモードでChromeを起動
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    browser = webdriver.Chrome(options=chrome_options)
    browser.implicitly_wait(5)

    logger.info('処理を開始します.')

    main(main_config)

    # ブラウザを閉じる
    browser.close()
    browser.quit()

    logger.info('処理が完了しました.')
    sys.exit(0)
