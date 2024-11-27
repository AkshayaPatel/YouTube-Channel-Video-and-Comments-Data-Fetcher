import googleapiclient.discovery
import googleapiclient.errors
import pandas as pd
import re
import urllib.parse
from constants import Constants


def get_youtube_client():
    """
    Initializes and returns the YouTube API client.

    Returns:
        youtube (Resource): The YouTube API client.
    """
    youtube = googleapiclient.discovery.build(
        'youtube', 'v3', developerKey=Constants.API_KEY)
    return youtube


def extract_channel_handle_from_url(url):
    """
    Extracts the channel handle from a YouTube channel URL.

    Args:
        url (str): The YouTube channel URL.

    Returns:
        str: The channel handle (e.g., @channelhandle).
    """
    # Parse the URL and extract the path
    parsed_url = urllib.parse.urlparse(url)
    if parsed_url.hostname == 'www.youtube.com':
        path = parsed_url.path
        match = re.match(r'/@([^/]+)', path)
        if match:
            return match.group(0)  # Return the full handle including '@'
        else:
            raise ValueError("Invalid YouTube channel URL.")
    else:
        raise ValueError("Invalid YouTube URL.")


# Fetch channel ID using the handle (e.g., @channelhandle)
def get_channel_id_by_handle(youtube, handle):
    """
    Fetches the YouTube channel ID by searching for the channel handle.

    Args:
        youtube (Resource): The YouTube API client.
        handle (str): The YouTube channel handle (e.g., @channelhandle).

    Returns:
        str: The YouTube channel ID, or None if not found.
    """
    try:
        request = youtube.search().list(
            part="snippet",
            q=handle,
            type="channel"
        )
        response = request.execute()

        if len(response['items']) == 0:
            print(f"No channel found for handle: {handle}")
            return None

        channel_id = response['items'][0]['snippet']['channelId']
        return channel_id
    except googleapiclient.errors.HttpError as err:
        print(f"An error occurred: {err}")
        return None


# Fetch videos from the channel by channel ID
def get_videos_from_channel(youtube, channel_id, max_results):
    """
    Fetches the video IDs from a YouTube channel using the channel ID.

    Args:
        youtube (Resource): The YouTube API client.
        channel_id (str): The YouTube channel ID.
        max_results (int): The maximum number of videos to retrieve.

    Returns:
        list: A list of video IDs.
    """
    video_ids = []
    try:
        request = youtube.channels().list(part="contentDetails", id=channel_id)
        response = request.execute()

        if 'items' not in response or len(response['items']) == 0:
            print(f"No channel data found for ID: {channel_id}")
            return []

        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Fetch video IDs from the uploads playlist
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        )
        response = request.execute()

        for item in response['items']:
            video_ids.append(item['snippet']['resourceId']['videoId'])

        return video_ids
    except googleapiclient.errors.HttpError as err:
        print(f"An error occurred: {err}")
        return []


# Get video details (title, description, view count, like count, etc.)
def get_video_details(youtube, video_ids):
    """
    Fetches detailed information about videos using their video IDs.

    Args:
        youtube (Resource): The YouTube API client.
        video_ids (list): List of video IDs.

    Returns:
        list: A list of dictionaries containing video details.
    """
    video_data = []

    try:
        # Fetch video details using the video IDs
        request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids)
        )
        response = request.execute()

        for item in response['items']:
            video_data.append({
                'Video ID': item['id'],
                'Title': item['snippet']['title'],
                'Description': item['snippet']['description'],
                'Published Date': item['snippet']['publishedAt'],
                'View Count': item['statistics'].get('viewCount', 0),
                'Like Count': item['statistics'].get('likeCount', 0),
                'Comment Count': item['statistics'].get('commentCount', 0),
                'Duration': format_duration(item['contentDetails']['duration']),
                'Thumbnail URL': item['snippet']['thumbnails']['default']['url'],
            })

        return video_data
    except googleapiclient.errors.HttpError as err:
        print(f"An error occurred: {err}")
        return []


# Format the ISO 8601 duration (e.g., PT2H12M57S) into a more readable format
def format_duration(duration):
    """
    Converts the ISO 8601 duration (e.g., PT2H12M57S) to a more readable format.

    Args:
        duration (str): The video duration in ISO 8601 format.

    Returns:
        str: The formatted duration as a string (e.g., "2 hours 12 minutes 57 seconds").
    """
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration)
    hours = match.group(1)
    minutes = match.group(2)
    seconds = match.group(3)

    # Extract numbers and format
    hours = hours[:-1] if hours else 0
    minutes = minutes[:-1] if minutes else 0
    seconds = seconds[:-1] if seconds else 0

    return f"{hours} hours {minutes} minutes {seconds} seconds"


# Get the latest 100 comments and replies across all videos
def get_comments(youtube, video_ids):
    """
    Fetches the latest 100 comments and replies for the provided video IDs.

    Args:
        youtube (Resource): The YouTube API client.
        video_ids (list): List of video IDs.

    Returns:
        list: A list of dictionaries containing comment data.
    """
    comments_data = []
    try:
        for video_id in video_ids:
            request = youtube.commentThreads().list(
                part="snippet,replies",
                videoId=video_id,
                textFormat="plainText",
                maxResults=100
            )
            response = request.execute()

            # Iterate through the comment threads
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comment_data = {
                    'Video ID': video_id,
                    'Comment ID': item['id'],
                    'Comment Text': comment['textDisplay'],
                    'Author Name': comment['authorDisplayName'],
                    'Published Date': comment['publishedAt'],
                    'Like Count': comment['likeCount'],
                    'Reply To': None  # Top-level comment has no reply-to
                }
                comments_data.append(comment_data)

                # If there are replies, get those too
                if 'replies' in item:
                    for reply in item['replies']['comments']:
                        reply_data = {
                            'Video ID': video_id,
                            'Comment ID': reply['id'],
                            'Comment Text': reply['snippet']['textDisplay'],
                            'Author Name': reply['snippet']['authorDisplayName'],
                            'Published Date': reply['snippet']['publishedAt'],
                            'Like Count': reply['snippet']['likeCount'],
                            'Reply To': item['id']  # This is a reply to the top-level comment
                        }
                        comments_data.append(reply_data)

            # Break after collecting 100 comments across all videos
            if len(comments_data) >= 100:
                break

        return comments_data[:100]  # Ensure we get only the latest 100 comments
    except googleapiclient.errors.HttpError as err:
        print(f"An error occurred: {err}")
        return []


# Save the data into Excel file
def save_data_to_excel(video_data, comments_data, file_name="youtube_data.xlsx"):
    """
    Saves the video and comment data to an Excel file.

    Args:
        video_data (list): List of video details.
        comments_data (list): List of comments data.
        file_name (str): The name of the Excel file to save.
    """
    # Convert video data and comments data to DataFrames
    video_df = pd.DataFrame(video_data)
    comments_df = pd.DataFrame(comments_data)

    # Save both DataFrames to an Excel file
    with pd.ExcelWriter(file_name, engine='xlsxwriter') as writer:
        video_df.to_excel(writer, sheet_name='Video Data', index=False)
        comments_df.to_excel(writer, sheet_name='Comments Data', index=False)

