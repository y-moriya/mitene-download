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
from google.auth.exceptions import RefreshError
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
                                                             ['https://www.googleapis.com/auth/photoslibrary.appendonly'])
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

# create album
def create_album(service, album_name):
    body = {
        'album': {'title': album_name}
    }
    response = service.albums().create(body=body).execute()
    logger.info(f"Album '{album_name}', id: '{response.get('id')}' created.")
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
    album_id = main_config['upload_album_id']

    # ログ設定ファイル読込
    with open('../log_config.yml', 'r', encoding='utf-8') as read_log_config:
        log_config = yaml.safe_load(read_log_config)

    config.dictConfig(log_config)
    logger = getLogger('logger')

    # 認証済みの API クライアントを作成
    try:
        creds = get_credentials()
    except RefreshError as e:
        print(f"Error refreshing the token: {e}")
        exit(1)

    service = build('photoslibrary', 'v1', credentials=creds,
                    static_discovery=False)

    # ファイルの一覧を取得
    files = os.listdir(dl_dir_path)

    # アルバムIDが定義されていなかった場合、アルバムを作成
    if album_id is None:
        album_id = create_album(service, album_name)

    # ファイルを Loop
    for file in files:
        path = f'{dl_dir_path}/{file}'
        # 画像と動画を同じ場所にアップロードする場合
        # # mimetypes でファイルのMIMETYPEを取得
        mime_type = mimetypes.guess_type(path)[0]
        if mime_type is None:
            continue

        if mime_type is not None and (mime_type.startswith('image') or mime_type.startswith('video')):
            response = upload_image(path, album_id)
            # アップロードに成功した場合
            if response is not None:
                # アップロードしたファイルは削除する
                os.remove(path)

        time.sleep(1)
