import os
import pickle
import requests
import piexif
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

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
      creds = flow.run_local_server(port=0)
    with open('token.pickle', 'wb') as token:
      pickle.dump(creds, token)
  return build('photoslibrary', 'v1', credentials=creds)

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
        request = service.mediaItems().get(mediaItemId=item['id'])
        media_item = request.execute()
        url = media_item['baseUrl'] + '=d'
        response = requests.get(url)
        with open(file_path, 'wb') as f:
          f.write(response.content)
        # Add Exif data
        exif_dict = piexif.load(file_path)
        creation_time = datetime.strptime(media_item['mediaMetadata']['creationTime'], '%Y-%m-%dT%H:%M:%S%z')
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = creation_time.strftime("%Y:%m:%d %H:%M:%S")
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
  album_id = 'your_album_id'  # Replace with your Google Photos album ID
  download_dir = 'your_download_dir'  # Replace with your download directory
  download_photos(service, album_id, download_dir)

if __name__ == '__main__':
  main()