#!/usr/bin/env python
# coding: utf-8

import yaml
import hashlib
import os
from logging import config, getLogger, StreamHandler, Formatter

# メイン設定ファイル読込
with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
    main_config = yaml.safe_load(read_main_config)

dl_dir_path = main_config['dl_dir_path'] + '/'

# ログ設定ファイル読込
with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
    log_config = yaml.safe_load(read_log_config)

config.dictConfig(log_config)
logger = getLogger('logger')

# ダウンロードフォルダ内のファイルのハッシュ値を取得
def list_hash():
    # ダウンロードフォルダ内のファイル名を取得
    file_list = os.listdir(dl_dir_path)
    # hash_list.txt があれば削除
    if 'hash_list.txt' in file_list:
        file_list.remove('hash_list.txt')
    # file_list の件数をログ出力
    logger.info('ダウンロードフォルダ内のファイルの件数: %s', len(file_list))
    # ダウンロードフォルダ内のファイルのハッシュ値を取得
    hash_list = []
    for file in file_list:
        with open(dl_dir_path + file, 'rb') as f:
            hash_list.append(hashlib.md5(f.read()).hexdigest())
    return hash_list

# ハッシュ値のリストをダウンロードフォルダにファイルにして上書き保存
def save_hash_list(hash_list):
    with open(dl_dir_path + 'hash_list.txt', 'w') as f:
        for hash in hash_list:
            f.write(hash + '\n')

# 実行
if __name__ == '__main__':
    hash_list = list_hash()
    save_hash_list(hash_list)
    # hash_list の件数をログ出力
    logger.info('ハッシュを計算したファイルの件数: %s', len(hash_list))
