import os
import pickle
import requests
import piexif
import imghdr
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import settings

# If modifying these SCOPES, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def service_auth():
  """
  サービスの認証を行い、認証されたサービスリソースを返します。

  Returns:
    googleapiclient.discovery.Resource: 認証されたサービスリソース。
  """
  creds = None
  if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
      creds = pickle.load(token)
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
      creds = flow.run_local_server(port=80, open_browser=False)
    with open('token.pickle', 'wb') as token:
      pickle.dump(creds, token)
  return build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

def download_photos(service, album_id, download_dir):
  """
  指定されたアルバムから写真をダウンロードします。

  Args:
    service: Google Photos API サービスオブジェクト
    album_id: ダウンロードする写真のアルバムID
    download_dir: ダウンロード先ディレクトリのパス

  Returns:
    None
  """
  next_page_token = ''
  while True:
    results = service.mediaItems().search(
      body={
        'albumId': album_id,
        'pageSize': 100,
        'pageToken': next_page_token if next_page_token else None
      }
    ).execute()
    items = results.get('mediaItems', [])
    for item in items:
      file_path = os.path.join(download_dir, item['filename'])
      if not os.path.exists(file_path):  # Only download new photos
        if item['mimeType'] == 'image/jpeg':  # Only save if the file is a JPEG image
          request = service.mediaItems().get(mediaItemId=item['id'])
          media_item = request.execute()
          url = media_item['baseUrl'] + '=d'
          response = requests.get(url)
          with open(file_path, 'wb') as f:
            f.write(response.content)
            print('Downloaded', file_path, 'at', datetime.now())
          # Add Exif data
          exif_dict = piexif.load(file_path)
          creation_time = datetime.strptime(media_item['mediaMetadata']['creationTime'], '%Y-%m-%dT%H:%M:%S%z')
          exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = creation_time.strftime("%Y:%m:%d %H:%M:%S")
          # Before calling piexif.dump
          if imghdr.what('', exif_dict["thumbnail"]) != 'jpeg':
            print("Thumbnail is not a JPEG. Skipping.")
          else:
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, file_path)
    next_page_token = results.get('nextPageToken')
    if not next_page_token:
      break

def main():
  """
  Google Photosから写真をダウンロードして、指定されたディレクトリに保存する関数です。

  Args:
    None

  Returns:
    None
  """
  service = service_auth()
  download_photos(service, settings.ALBUM_ID, settings.DESTINATION_DIR)

# アルバム一覧を取得する
#  nextPageToken = ''
#  sharedAlbums = service.sharedAlbums().list(pageSize=20,pageToken=nextPageToken).execute()
#  print(sharedAlbums)

if __name__ == '__main__':
  main()