#!/usr/bin/env python
# coding: utf-8

import os
import sys

import pandas as pd

from mitene_scraper import MiteneScraper

if __name__ == '__main__':
    with MiteneScraper() as scraper:
        last_downloaded_date_file = '../last_downloaded_date.txt'

        # 引数を取得
        args = sys.argv

        # 引数が2つある場合
        if len(args) == 3:
            # 実行時引数からstart_dateとend_dateを取得
            # 引数が日付形式でない場合はエラーを出力して終了
            try:
                start_date = pd.to_datetime(args[1])
                end_date = pd.to_datetime(args[2])
            except ValueError:
                scraper.log_error('日付形式が正しくありません. YYYY-MM-DDの形式で入力してください.')
                sys.exit(1)

        # 引数がなく、last_downloaded_date.txt がない場合
        elif len(args) == 1 and not os.path.exists(last_downloaded_date_file):
            # エラーを出力して終了
            scraper.log_error('引数がありません. YYYY-MM-DDの形式で入力してください.')
            sys.exit(1)

        # 引数がなく、last_downloaded_date.txt がある場合
        elif len(args) == 1 and os.path.exists(last_downloaded_date_file):
            # last_downloaded_date.txt の内容を読み込む
            with open(last_downloaded_date_file, 'r') as f:
                # ファイル内容から日付を取得
                # end_date は今日の日付
                try:
                    start_date = pd.to_datetime(f.read())
                    end_date = pd.to_datetime('today')
                # ファイル内容が日付形式でない場合はエラーを出力して終了
                except ValueError:
                    scraper.log_error(
                        'last_downloaded_date.txt の日付形式が正しくありません. YYYY-MM-DDの形式で入力してください.')
                    sys.exit(1)
        # それ以外の場合はエラーを出力して終了
        else:
            scraper.log_error(
                'last_downloaded_date.txt の読み込み、または引数の読み込みに失敗しました.')
            sys.exit(1)

        # ダウンロード開始日と終了日をログに出力
        scraper.log_info(f'ダウンロード開始日: {start_date.strftime("%Y-%m-%d")}')
        scraper.log_info(f'ダウンロード終了日: {end_date.strftime("%Y-%m-%d")}')

        # ダウンロード開始日と終了日を指定して実行
        scraper.run_by_date(start_date, end_date)

        # last_downloaded_date_file に最終DL日を書き込む
        with open(last_downloaded_date_file, 'w') as f:
            f.write(end_date.strftime('%Y-%m-%d'))

        scraper.log_info('処理が完了しました.')
        sys.exit(0)
