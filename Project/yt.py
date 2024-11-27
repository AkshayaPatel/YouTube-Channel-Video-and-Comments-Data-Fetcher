from utils import get_youtube_client, extract_channel_handle_from_url, get_channel_id_by_handle, \
    get_videos_from_channel, get_video_details, get_comments, save_data_to_excel


# Main function
def main(channel_url, max_videos=50):
    """
    Main function to run the script. Takes a YouTube channel URL, fetches video and comment data,
    and saves the results to an Excel file.

    Args:
        channel_url (str): The full YouTube channel URL (e.g., https://www.youtube.com/@channelhandle).
    """
    youtube = get_youtube_client()

    # Extract the channel handle from the URL
    try:
        channel_handle = extract_channel_handle_from_url(channel_url)
        print(f"Extracted channel handle: {channel_handle}")
    except ValueError as e:
        print(e)
        return

    # Fetch channel ID from the handle
    channel_id = get_channel_id_by_handle(youtube, channel_handle)
    if not channel_id:
        print("Could not fetch channel ID. Exiting.")
        return

    print(f"Fetched channel ID: {channel_id}")

    # Get video IDs from the channel
    video_ids = get_videos_from_channel(youtube, channel_id, max_videos)
    if not video_ids:
        print("No videos found for the channel.")
        return

    # Get video details
    video_data = get_video_details(youtube, video_ids)

    # Get comments and replies
    comments_data = get_comments(youtube, video_ids)

    # Save the data to an Excel file
    save_data_to_excel(video_data, comments_data)
    print(f"Data saved to 'youtube_data.xlsx'.")


# Example usage
if __name__ == "__main__":
    channel_url = "https://www.youtube.com/@Telsuko"  # Replace with the desired channel URL
    max_videos = 70  # No of videos you want to retrieve from the channel
    main(channel_url, max_videos)
