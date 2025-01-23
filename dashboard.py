import json
import pandas as pd
import isodate
import streamlit as st
import plotly.express as px
from sklearn.feature_extraction.text import TfidfVectorizer


# Function to load liked videos from a JSON file
def load_liked_videos(file_path):
    try:
        with open(file_path, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        st.error("Error loading the JSON file. Please check the file path or content.")
        st.stop()


# Function to format duration in seconds to H:M:S
def format_duration(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    elif minutes > 0:
        return f"{int(minutes)}m {int(seconds)}s"
    else:
        return f"{int(seconds)}s"


# Function to parse ISO 8601 duration format to seconds
def parse_duration(duration):
    return isodate.parse_duration(duration).total_seconds()


# YouTube video category names
category_names = {
    1: "Film & Animation",
    2: "Autos & Vehicles",
    10: "Music",
    15: "Pets & Animals",
    17: "Sports",
    18: "Short Movies",
    19: "Travel & Events",
    20: "Gaming",
    21: "Videoblogging",
    22: "People & Blogs",
    23: "Comedy",
    24: "Entertainment",
    25: "News & Politics",
    26: "Howto & Style",
    27: "Education",
    28: "Science & Technology",
    29: "Nonprofits & Activism",
    30: "Movies",
    31: "Anime/Animation",
    32: "Action/Adventure",
    33: "Classics",
    34: "Comedy",
    35: "Documentary",
    36: "Drama",
    37: "Family",
    38: "Foreign",
    39: "Horror",
    40: "Sci-Fi/Fantasy",
    41: "Thriller",
    42: "Shorts",
    43: "Shows",
    44: "Trailers",
}

# Initialize Streamlit
st.title("Liked Videos")

# Load liked videos data
liked_videos = load_liked_videos("liked.json")

# Extract relevant data into a DataFrame
video_data = [
    {
        "title": video_info["video_data"]["snippet"].get("title", "Unknown"),
        "id": video_info["video_data"].get("id", "Unknown"),
        "duration": format_duration(
            parse_duration(
                video_info["video_data"]["contentDetails"].get("duration", "PT0S")
            )
        ),
        "channel": video_info["video_data"]["snippet"].get("channelTitle", "Unknown"),
        "publishedAt": pd.to_datetime(
            video_info["video_data"]["snippet"].get("publishedAt", None)
        ),
        "likedAt": pd.to_datetime(video_info["playlist_data"].get("publishedAt", None)),
    }
    for video_info in liked_videos.values()
    if "video_data" in video_info
]
df = pd.DataFrame(video_data)

# Filter videos based on published date range
if not df.empty:
    min_date, max_date = st.slider(
        "Date Video Published by Channel",
        min_value=df["publishedAt"].min().date(),
        max_value=df["publishedAt"].max().date(),
        value=(df["publishedAt"].min().date(), df["publishedAt"].max().date()),
        format="YYYY-MM-DD",
    )
    df_filtered = df[
        (df["publishedAt"].dt.date >= min_date)
        & (df["publishedAt"].dt.date <= max_date)
    ]

    # Filter videos based on liked date range
    min_liked_date, max_liked_date = st.slider(
        "Date Video Added to Liked Videos",
        min_value=df["likedAt"].min().date(),
        max_value=df["likedAt"].max().date(),
        value=(df["likedAt"].min().date(), df["likedAt"].max().date()),
        format="YYYY-MM-DD",
    )
    df_filtered = df_filtered[
        (df_filtered["likedAt"].dt.date >= min_liked_date)
        & (df_filtered["likedAt"].dt.date <= max_liked_date)
    ]

    # Search for video titles or channels
    search_query = st.text_input("Search for video titles or channels")
    if search_query:
        df_filtered = df_filtered[
            df_filtered["title"].str.contains(search_query, case=False, na=False)
            | df_filtered["channel"].str.contains(search_query, case=False, na=False)
        ]

    # Filter by selected channel
    selected_channel = st.selectbox(
        "Select a channel to filter",
        options=["All"] + sorted(df_filtered["channel"].unique().tolist()),
    )
    if selected_channel != "All":
        df_filtered = df_filtered[df_filtered["channel"] == selected_channel]

    # Check if the filtered DataFrame is empty
    if df_filtered.empty:
        st.warning("No videos match the current filters.")
        st.stop()

    # Display total number of videos
    data = {
        "": ["Total number of videos", "Number of videos in the selected date range"],
        "videos": [len(df), len(df_filtered)],
    }

    df_display = pd.DataFrame(data)
    st.table(df_display)

    # Display filtered videos
    st.dataframe(df_filtered)

    # Channel video count visualization
    channel_video_count = df_filtered["channel"].value_counts().reset_index()
    channel_video_count.columns = ["channel", "video_count"]
    fig = px.bar(
        channel_video_count.head(10),
        x="channel",
        y="video_count",
        title="Top 10 Channels by Video Count",
    )
    st.plotly_chart(fig)

    # Extract and count categories from filtered videos
    categories = [
        video_info["video_data"]["snippet"].get("categoryId")
        for video_info in liked_videos.values()
        if "video_data" in video_info
        and video_info["video_data"].get("id") in df_filtered["id"].values
    ]
    categories = [c for c in categories if c is not None]
    category_counts = pd.Series(categories).value_counts().reset_index(name="count")
    category_counts.columns = ["category", "count"]
    category_counts["category"] = (
        category_counts["category"].astype(int).map(category_names)
    )

    # Category count visualization
    fig = px.bar(
        category_counts, x="category", y="count", title="Most Popular Categories"
    )
    st.plotly_chart(fig)

    # Video durations distribution visualization
    durations = [
        parse_duration(
            video_info["video_data"]["contentDetails"].get("duration", "PT0S")
        )
        for video_info in liked_videos.values()
        if "video_data" in video_info
        and video_info["video_data"].get("id") in df_filtered["id"].values
    ]
    duration_df = pd.DataFrame(durations, columns=["duration"])
    upper_limit = duration_df["duration"].quantile(1)
    filtered_duration_df = duration_df[duration_df["duration"] <= upper_limit]

    fig = px.histogram(
        filtered_duration_df,
        x="duration",
        title="Distribution of Video Durations",
        log_y=True,
        nbins=30,
    )
    st.plotly_chart(fig)

    # Duration statistics
    min_duration, max_duration, avg_duration = (
        filtered_duration_df["duration"].min(),
        filtered_duration_df["duration"].max(),
        filtered_duration_df["duration"].mean(),
    )
    duration_stats = {
        "Statistic": ["Min", "Max", "Mean", "Median", "Mode"],
        "Duration": [
            format_duration(min_duration),
            format_duration(max_duration),
            format_duration(avg_duration),
            format_duration(filtered_duration_df["duration"].median()),
            format_duration(filtered_duration_df["duration"].mode().values[0]),
        ],
    }
    st.table(pd.DataFrame(duration_stats))

    # Extract and count tags from filtered videos
    tags = [
        tag
        for video_info in liked_videos.values()
        if "video_data" in video_info and "tags" in video_info["video_data"]["snippet"]
        for tag in video_info["video_data"]["snippet"].get("tags", [])
        if video_info["video_data"].get("id") in df_filtered["id"].values
    ]
    tag_counts = pd.Series(tags).value_counts().reset_index(name="count")
    tag_counts.columns = ["tag", "count"]
    fig = px.bar(
        tag_counts.head(10), x="tag", y="count", title="Top 10 Most Popular Tags"
    )
    st.plotly_chart(fig)

    # TF-IDF analysis for video titles
    video_titles = [
        video_info["video_data"]["snippet"].get("title", "")
        for video_info in liked_videos.values()
        if "video_data" in video_info
        and video_info["video_data"].get("id") in df_filtered["id"].values
    ]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform(video_titles)
    tfidf_scores = tfidf_matrix.sum(axis=0).A1
    tfidf_df = pd.DataFrame(
        {"word": vectorizer.get_feature_names_out(), "score": tfidf_scores}
    ).sort_values(by="score", ascending=False)
    st.write("**Top 10 Words by TF-IDF Score:**")
    st.dataframe(tfidf_df.head(10).reset_index(drop=True), width=800)
else:
    st.warning("The dataset is empty or invalid.")
