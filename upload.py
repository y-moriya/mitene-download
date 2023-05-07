import yaml
import os
import mimetypes
from logging import config, getLogger
import pickle
import time
import requests
import shutil
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

# OAuth 2.0 認証
def get_credentials():
    creds = None
    token_path = '../token.pickle'
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('../client_secrets.json',
                                                             ['https://www.googleapis.com/auth/photoslibrary'])
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds


def get_upload_token(image_path):
    # create header
    headers = {
        'Authorization': 'Bearer ' + get_credentials().token,
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-Content-Type': mimetypes.guess_type(image_path)[0],
        'X-Goog-Upload-Protocol': "raw"
    }

    # upload image
    image_file = open(image_path, 'rb')
    image_bytes = image_file.read()
    image_file.close()
    response = requests.post(
        'https://photoslibrary.googleapis.com/v1/uploads', headers=headers, data=image_bytes)

    return response.content.decode('utf-8')


def get_album_id(service, album_name):
    album_id = None
    next_page_token = None
    while not album_id:
        response = service.albums().list(pageSize=50, pageToken=next_page_token).execute()
        albums = response.get("albums", [])

        for album in albums:
            if album["title"] == album_name:
                album_id = album["id"]
                logger.info(f"Album '{album_name}', id: '{album_id}' found.")
                break

        next_page_token = response.get("nextPageToken", None)
        if not next_page_token:
            break

    if not album_id:
        logger.info(f"Album '{album_name}' not found.")
        return None

    else:
        return album_id

# create album
def create_album(service, album_name):
    body = {
        'album': {'title': album_name}
    }
    response = service.albums().create(body=body).execute()
    logger.info(f"Album '{album_name}' created.")
    return response.get('id')

# 画像を Google Photos にアップロード
def upload_image(image_path, album_id):
    try:
        upload_token = get_upload_token(image_path)

        # create header
        headers = {
            'Authorization': 'Bearer ' + get_credentials().token,
            'Content-type': 'application/json'
        }

        # upload image
        response = requests.post(
            'https://photoslibrary.googleapis.com/v1/mediaItems:batchCreate',
            headers=headers,
            json={
                'albumId': album_id,
                'newMediaItems': [
                    {
                        'description': 'from upload.py',
                        'simpleMediaItem': {
                            "fileName": image_path,
                            'uploadToken': upload_token
                        }
                    }
                ]
            }
        )

        if response.status_code != 200:
            logger.error(f"Upload Error: {image_path}, {response.text}, {response.status_code}")
            response = None
        else:
            logger.info(f"Upload Success: {image_path}")
    except HttpError as error:
        logger.error(f"An error occurred: {error}")
        response = None
    return response

# 実行
if __name__ == '__main__':
    # メイン設定ファイル読込
    with open('../main_config.yml', 'r', encoding='utf-8') as read_main_config:
        main_config = yaml.safe_load(read_main_config)

    dl_dir_path = main_config['dl_dir_path']
    album_name = main_config['upload_album_name']
    video_move_path = main_config['video_move_path']

    # ログ設定ファイル読込
    with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
        log_config = yaml.safe_load(read_log_config)

    config.dictConfig(log_config)
    logger = getLogger('logger')

    # 認証済みの API クライアントを作成
    creds = get_credentials()
    service = build('photoslibrary', 'v1', credentials=creds,
                    static_discovery=False)

    # ファイルの一覧を取得
    files = os.listdir(dl_dir_path)

    # アルバムIDを取得
    album_id = get_album_id(service, album_name)

    # アルバムIDが取得できなかった場合、アルバムを作成
    if album_id is None:
        album_id = create_album(service, album_name)

    # ファイルを Loop
    for file in files:
        path = f'{dl_dir_path}/{file}'
        # mimetypes でファイルのMIMETYPEを取得
        mime_type = mimetypes.guess_type(path)[0]
        # ファイルのMIMETYPEがNoneTypeではなく、かつ、画像の場合
        if mime_type is not None and mime_type.startswith('image'):
            # 画像をアップロード
            response = upload_image(path, album_id)
            # アップロードに成功した場合
            if response is not None:
                # アップロードしたファイルは削除する
                os.remove(path)
        # ファイルのMIMETYPEがNoneTypeではなく、かつ、動画の場合
        elif mime_type is not None and mime_type.startswith('video'):
            # D:\Amazon Drive\Amazon Drive\ビデオ に動画を移動
            shutil.move(path, video_move_path)
            logger.info(f"Move Success: {path}")

        # sleep 1
        time.sleep(1)
