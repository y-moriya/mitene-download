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
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager


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

        # 一時ダウンロードディレクトリを指定
        prefs = {'download.default_directory': self.tmp_dl_dir_path}
        chrome_options.add_experimental_option('prefs', prefs)

        self.browser = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
        self.browser.implicitly_wait(5)

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
        try:
            button = self.browser.find_element(By.CLASS_NAME, class_name)
            # self.logger.debug('button要素: %s', button)
            # self.logger.debug('buttonのテキスト: %s', button.text)
            # self.logger.debug('buttonの表示状態: %s', button.is_displayed())
            # self.logger.debug('buttonの有効状態: %s', button.is_enabled())
            
            time.sleep(self.click_wait_time)
            
            actions = ActionChains(self.browser)
            actions.move_to_element(button).click().perform()
            self.logger.info('buttonをクリックしました: %s', class_name)
        except Exception as e:
            self.logger.error('buttonのクリックに失敗しました: %s', e)

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
    def process_downloaded_file(self, shooting_date, tmp_file_path):
        file_hash = hashlib.md5(
            open(tmp_file_path, 'rb').read()).hexdigest()

        if not os.path.exists(self.dl_dir_path + '/hash_list.txt'):
            # ファイルが存在しない場合は作成する
            with open(self.dl_dir_path + '/hash_list.txt', 'w') as f:
                f.write('')
            self.logger.info('hash_list.txt を作成しました.')

        with open(self.dl_dir_path + '/hash_list.txt', 'r') as f:
            hash_list = f.read().splitlines()

        if file_hash in hash_list:
            self.logger.info(
                '既存ファイルが存在するため、一時保存フォルダから削除します. ハッシュ: %s', file_hash)
            os.remove(tmp_file_path)
        else:
            with open(self.dl_dir_path + '/hash_list.txt', 'a') as f:
                f.write(file_hash + '\n')

            extension = os.path.splitext(tmp_file_path)[1]
            new_file_name = shooting_date + '_' + file_hash + extension
            new_file_path = self.dl_dir_path + '/' + new_file_name
            shutil.move(tmp_file_path, new_file_path)
            self.logger.info('ダウンロード完了. ファイル名: %s', new_file_name)

        time.sleep(5)

    # ダウンロードを待機しつつファイルを処理する
    def download_and_process_file(self):
        shooting_date = self.get_shooting_date()
        self.logger.info('ダウンロードを開始します.')
        self.logger.info('撮影日: %s', shooting_date)

        self.click_on_the_overlay('download-button')

        for i in range(self.dl_wait_time + 1):
            if i != 0 and i % 30 == 0:
                self.logger.debug(str(i) + '秒経過')

            download_files = glob.glob(self.tmp_dl_dir_path + '/' + '*.*')

            if download_files:
                tmp_file_path = download_files[0]
                extension = os.path.splitext(tmp_file_path)[1]

                if '.crdownload' not in extension:
                    self.process_downloaded_file(shooting_date, tmp_file_path)
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

        # 最大ページ数が取得できないため、最終ページまでループする
        for i in range(1, 10**4, 1):
            self.logger.info('%sページ目', str(i))
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
                break

    def run_newsfeed(self):
        # 近況ページ newsfeeds を開く
        self.browser.get(self.url + '/newsfeeds')
        self.browser.implicitly_wait(5)

        # ダウンロード対象のニュースフィードIDを取得
        target_newsfeed_ids = self.get_target_newsfeed_ids()

        if target_newsfeed_ids:
            for newsfeed_id in target_newsfeed_ids:
                self.process_newsfeed(newsfeed_id)

    def run_newsfeed_all(self):
        # 近況ページ newsfeeds を開く
        self.browser.get(self.url + '/newsfeeds')
        self.browser.implicitly_wait(5)

        # 全てをダウンロードする場合は「もっと見る」ボタンが消えるまでクリック
        self.logger.info('全ての近況をダウンロードします.')
        self.click_see_more()

        # ダウンロード対象のニュースフィードIDを取得
        target_newsfeed_ids = self.get_target_newsfeed_ids()

        if target_newsfeed_ids:
            for newsfeed_id in target_newsfeed_ids:
                self.process_newsfeed(newsfeed_id)

    def run_by_date(self, start_date, end_date):
        for page in range(1, 10**4, 1):
            # ページ内のサムネイルの数を数える
            thumbnails = self.browser.find_elements(By.CLASS_NAME, 'media-img')

            # サムネイルをクリックしてオーバーレイを表示
            self.click_on_the_overlay('media-img')

            # ページ内の最大撮影日を取得
            max_date_on_page = self.browser.find_element(By.CLASS_NAME, 'media-took-at').text
            max_date_on_page = pd.to_datetime(max_date_on_page, format='%m/%d/%Y').strftime('%Y-%m-%d')

            # [<]ボタンをクリック
            self.click_on_the_overlay('prev-button')

            # ページ内の最小撮影日を取得
            min_date_on_page = self.browser.find_element(By.CLASS_NAME, 'media-took-at').text
            min_date_on_page = pd.to_datetime(min_date_on_page, format='%m/%d/%Y').strftime('%Y-%m-%d')

            # [x]ボタンをクリック
            self.click_on_the_overlay('close-button')

            self.logger.info('%sページ目 画像・動画数:%s 撮影日:%sから%s',
                        str(page), str(len(thumbnails)),
                        min_date_on_page, max_date_on_page)

            # ページ内にダウンロード対象ページがあるか確認
            if start_date > pd.to_datetime(max_date_on_page):
                self.logger.info('このページ以降の画像・動画は全てDL対象期間外に撮影されたものです.')
                self.logger.info('処理を終了します.')
                break

            elif pd.to_datetime(min_date_on_page) > end_date:
                self.logger.info('DL対象期間に撮影された画像・動画はページ内に存在しません.')

            else:
                self.logger.info('ページ内からDL対象期間に撮影された画像・動画を検索します.')

                # サムネイルをクリックしてオーバーレイを表示
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
                break

    def log_info(self, message):
        self.logger.info(message)

    def log_error(self, message):
        self.logger.error(message)

    def close(self):
        self.browser.close()
        self.browser.quit()

    # For use with the "with" statement
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
