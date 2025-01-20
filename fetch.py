import json
import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


# YouTube API setup
CLIENT_SECRETS_FILE = "./client_secret.json"
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


# Authenticate and get the YouTube API client
def get_authenticated_service():
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES
    )
    credentials = flow.run_local_server(port=8080)
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials
    )


# Fetch all liked videos
def get_liked_videos_from_playlist(youtube):
    playlist_id = "LL"
    videos = {}
    next_page_token = None

    while True:
        try:
            request = youtube.playlistItems().list(
                part="snippet",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()
        except googleapiclient.errors.HttpError as e:
            print(f"An error occurred: {e}")
            break

        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            videos[snippet.get("resourceId", {}).get("videoId")] = {
                "playlist_data": snippet
            }

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return videos


def get_video_details(youtube, video_ids):
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=",".join(video_ids),
    )
    response = request.execute()
    return response["items"]


def main():

    CREDENTIALS_FILE = "./credentials.pkl"

    def save_credentials(credentials):
        with open(CREDENTIALS_FILE, "wb") as f:
            pickle.dump(credentials, f)

    def load_credentials():
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "rb") as f:
                return pickle.load(f)
        return None

    credentials = load_credentials()
    if not credentials:
        youtube = get_authenticated_service()
        save_credentials(youtube._http.credentials)
    else:
        youtube = googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=credentials
        )

    liked_videos = get_liked_videos_from_playlist(youtube)

    video_ids = list(liked_videos.keys())
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        video_details = get_video_details(youtube, batch)
        for video in video_details:
            liked_videos[video["id"]]["video_data"] = video

    with open(
        "./liked.json", "w"
    ) as json_file:
        json.dump(liked_videos, json_file, indent=4)


if __name__ == "__main__":
    main()
