import glob
import hashlib
import os
import re
import shutil
import sys
import time
from logging import config, getLogger

import pandas as pd
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class MiteneScraper:
    def __init__(self):
        with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
            main_config = yaml.safe_load(read_main_config)
        self.url = main_config['mitene_url']
        self.password = main_config['mitene_password']
        self.dl_dir_path = main_config['dl_dir_path']
        self.dl_wait_time = main_config['dl_wait_time']
        self.click_wait_time = main_config['click_wait_time']
        self.tmp_dl_dir_path = os.getcwd()

        # ログ設定ファイル読込
        with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
            log_config = yaml.safe_load(read_log_config)

        config.dictConfig(log_config)
        self.logger = getLogger('logger')

        # Chromeオプションを適用しヘッドレスモードでChromeを起動
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.implicitly_wait(5)

        self.is_download_all = (len(sys.argv) == 2 and sys.argv[1] == '--all')

        # 「みてね」のサイトを開く
        self.browser.get(self.url)
        self.browser.implicitly_wait(5)

        # 現在のURLを取得
        cur_url = self.browser.current_url

        # 現在のページがログインページの場合はパスワードを入力してログイン
        if cur_url.endswith(('login', 'login/')):
            self.login()
        else:
            self.logger.info('現在のページのURL: %s', cur_url)

    # オーバーレイ上のボタンをクリックする関数
    def click_on_the_overlay(self, class_name):
        button = self.browser.find_element(By.CLASS_NAME, class_name)
        time.sleep(self.click_wait_time)
        self.browser.execute_script("arguments[0].click();", button)

    # 撮影日を取得する
    def get_shooting_date(self):
        # 撮影日を取得
        shooting_date = self.browser.find_element(
            By.CLASS_NAME, 'media-took-at').text
        # shooting_date は 'MM/DD/YYYY' の形式なので 'YYYY-MM-DD' の形式に変換
        shooting_date = pd.to_datetime(
            shooting_date, format='%m/%d/%Y').strftime('%Y-%m-%d')
        return shooting_date

    # [次へ]ボタンが有効か無効かを判定する
    def is_next_button_enabled(self):
        next_btn = self.browser.find_element(By.CLASS_NAME, 'next')
        next_btn_tag_a = next_btn.find_element(By.TAG_NAME, 'a')
        next_btn_tag_a_attr_value = next_btn_tag_a.get_attribute("class")
        return next_btn_tag_a_attr_value == 'follower-paging-next-link'

    # ダウンロードされたファイルを処理する
    def process_downloaded_file(self, shooting_date):
        file_hash = hashlib.md5(
            open(self.tmp_file_path, 'rb').read()).hexdigest()

        with open(self.dl_dir_path + '/hash_list.txt', 'r') as f:
            hash_list = f.read().splitlines()

        if file_hash in hash_list:
            self.logger.info(
                '既存ファイルが存在するため、一時保存フォルダから削除します. ハッシュ: %s', file_hash)
            os.remove(self.tmp_file_path)
        else:
            with open(self.dl_dir_path + '/hash_list.txt', 'a') as f:
                f.write(file_hash + '\n')

            extension = os.path.splitext(self.tmp_file_path)[1]
            new_file_name = shooting_date + '_' + file_hash + extension
            new_file_path = self.dl_dir_path + '/' + new_file_name
            shutil.move(self.tmp_file_path, new_file_path)
            self.logger.info('ダウンロード完了. ファイル名: %s', new_file_name)

        time.sleep(5)

    # ダウンロードを待機しつつファイルを処理する
    def download_and_process_file(self):
        shooting_date = self.get_shooting_date()
        self.logger.info('ダウンロードを開始します.')

        self.click_on_the_overlay('download-button')

        for i in range(self.dl_wait_time + 1):
            if i != 0 and i % 30 == 0:
                self.logger.debug(str(i) + '秒経過')

            download_files = glob.glob(self.tmp_dl_dir_path + '/' + '*.*')

            if download_files:
                tmp_file_path = download_files[0]
                extension = os.path.splitext(tmp_file_path)[1]

                if '.crdownload' not in extension:
                    self.process_downloaded_file(shooting_date)
                    break

            if i >= self.dl_wait_time:
                self.logger.error('タイムアウトしました. DLを中断します.')
                sys.exit(1)

            time.sleep(1)

        self.click_on_the_overlay('next-button')

    # See More をクリックする
    def click_see_more(self):
        # 「もっと見る」ボタンを取得
        element = self.browser.find_element(
            By.CLASS_NAME, 'newsfeed-more-link')
        while element:
            self.browser.implicitly_wait(5)
            if element.text == 'See More':
                self.click_on_the_overlay('newsfeed-more-link')
                element = self.browser.find_element(
                    By.CLASS_NAME, 'newsfeed-more-link')
            else:
                return

    def login(self):
        cur_url = self.browser.current_url
        self.logger.info('現在のページのURL: %s', cur_url)
        self.logger.info('ログインします.')

        # パスワードを入力
        element = self.browser.find_element(By.ID, 'session_password')
        element.clear()
        element.send_keys(self.password)

        # ログインボタンをクリック
        login_button = self.browser.find_element(By.NAME, 'commit')
        self.browser.implicitly_wait(5)
        login_button.click()
        cur_url = self.browser.current_url

        if cur_url == self.url:
            self.logger.info('現在のページのURL: %s', cur_url)
            self.logger.info('ログインに成功しました.')

    def get_target_newsfeed_ids(self):
        # ダウンロード済みの最新のニュースフィードIDを取得
        if not os.path.exists(self.dl_dir_path + '/newsfeed_id_list.txt'):
            # ファイルが存在しない場合は作成する
            with open(self.dl_dir_path + '/newsfeed_id_list.txt', 'w') as f:
                f.write('')
            self.logger.info('newsfeed_id_list.txt を作成しました.')

        with open(self.dl_dir_path + '/newsfeed_id_list.txt', 'r') as f:
            newsfeed_id_list = f.read().splitlines()

        photos_pattern = re.compile(
            r"\d+ new photos?/videos? have been added.")
        target_newsfeed_ids = []
        for p_element in self.browser.find_elements(By.TAG_NAME, "p"):
            if photos_pattern.match(p_element.text):
                # parent の a タグの href 属性を取得
                parent_element = p_element.find_element(
                    By.XPATH, '../../../..')
                href = parent_element.get_attribute('href')

                # r'newsfeeds/(\d+)' に一致する文字列を取得
                match = re.search(r'newsfeeds/(\d+)', href)
                if match:
                    # \d+ 部分を取得
                    newsfeed_id = match.group(1)
                    if newsfeed_id in newsfeed_id_list:
                        self.logger.info(
                            'newsfeed_id: %s はダウンロード済みです.', newsfeed_id)
                        continue
                    else:
                        target_newsfeed_ids.append(newsfeed_id)

                else:
                    self.logger.info('newsfeed_id が存在しないためスキップします.')
                    continue
        return target_newsfeed_ids

    def process_newsfeed(self, newsfeed_id):
        self.browser.get(self.url + '/newsfeeds/' + newsfeed_id)

        self.logger.info('newsfeed_id: %s をダウンロードします.', newsfeed_id)
        self.logger.info('ページ内から画像・動画を検索します.')

        thumbnails = self.browser.find_elements(By.CLASS_NAME, 'media-img')
        self.click_on_the_overlay('media-img')

        for _ in range(len(thumbnails)):
            self.download_and_process_file()

        self.click_on_the_overlay('close-button')

        if self.is_next_button_enabled():
            self.logger.info('次のページに遷移します.')
            next_button = self.browser.find_element(
                By.CLASS_NAME, 'follower-paging-next-link')
            next_button.click()
            time.sleep(1)
        else:
            self.logger.info('このページが最終ページです.')
            self.logger.info('処理を終了します.')
            with open(self.dl_dir_path + '/newsfeed_id_list.txt', 'a') as f:
                f.write(newsfeed_id + '\n')

    def run_newsfeed(self):
        # 近況ページ newsfeeds を開く
        self.browser.get(self.url + '/newsfeeds')
        self.browser.implicitly_wait(5)

        # 全てをダウンロードするフラグが立っている場合は「もっと見る」ボタンが消えるまでクリック
        if self.is_download_all:
            self.logger.info('全ての近況をダウンロードします.')
            self.click_see_more()

        # ダウンロード対象のニュースフィードIDを取得
        target_newsfeed_ids = self.get_target_newsfeed_ids()

        if target_newsfeed_ids:
            for newsfeed_id in target_newsfeed_ids:
                self.process_newsfeed(newsfeed_id)

    def close(self):
        self.browser.quit()

    # For use with the "with" statement
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
