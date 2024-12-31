import pandas as pd
import streamlit as st

# Function to calculate scores with the new condition
def calculate_scores(data):
    results = []

    for user_id, group in data.groupby("user_id"):
        # Filtering lessons with at least 90% watched
        group["start_time"] = pd.to_datetime(group["start_time"], errors='coerce')  # Ensure correct datetime conversion
        group["end_time"] = pd.to_datetime(group["end_time"], errors='coerce')      # Ensure correct datetime conversion
        
        valid_lessons = []
        
        for lesson_id, lesson_group in group.groupby("lesson_id"):
            total_playback_minutes = lesson_group["playback_minutes"].sum()  # Total playback minutes for the lesson
            total_duration = (lesson_group["end_time"].max() - lesson_group["start_time"].min()).total_seconds() / 60  # Duration in minutes
            
            watched_percentage = (total_playback_minutes / total_duration) * 100 if total_duration > 0 else 0

            # Add lesson to valid_lessons if watched more than 90%
            if watched_percentage >= 90:
                valid_lessons.append(lesson_group)

        # Combine valid lessons
        valid_lessons = pd.concat(valid_lessons) if valid_lessons else pd.DataFrame()

        # Calculate interaction score for valid lessons only
        if not valid_lessons.empty:
            less_interacted_videos = valid_lessons[(valid_lessons["_pause"] + valid_lessons["_seek"]) < 3]  # Corrected to refer to _pause and _seek columns
            interaction_percentage = len(less_interacted_videos) / len(valid_lessons) * 100
            interaction_score = 10 if interaction_percentage >= 80 else 8 if interaction_percentage >= 50 else 5
        else:
            interaction_score = 0  # No valid lessons, so no score
        
        # Scoring 2: Videos watched offline
        offline_videos = group[group["_pb_type"] == 2]
        offline_percentage = len(offline_videos) / len(group) * 100
        offline_score = 10 if offline_percentage >= 90 else 9 if offline_percentage >= 50 else 5

        # Scoring 3: Total sessions per lesson_id
        session_score = 10
        for lesson_id, lesson_group in group.groupby("lesson_id"):
            lesson_group = lesson_group.sort_values("start_time")
            end_times = lesson_group["end_time"].shift(1)
            start_times = lesson_group["start_time"]
            session_gaps = start_times - end_times

            # Filter out non-valid session gaps (NaT)
            session_gaps = session_gaps.dropna()

            session_count = (session_gaps > pd.Timedelta(minutes=1)).sum() + 1  # Count sessions (threshold 1 minute)
            if session_count > 5:
                session_score -= 1  # Reduce score for excessive sessions

        # Append results
        total_score = (interaction_score + offline_score + session_score) / 3
        results.append({
            "user_id": user_id,
            "interaction_score": interaction_score,
            "offline_score": offline_score,
            "session_score": session_score,
            "total_score": total_score
        })

    return pd.DataFrame(results)

# Streamlit App
st.title("User Video Scoring System")

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

if uploaded_file:
    data = pd.read_csv(uploaded_file)
    st.write("Uploaded Data:")
    st.dataframe(data)
    
    # Clean column names
    data.columns = data.columns.str.strip()
    
    # Ensure necessary columns are present
    required_columns = ["user_id", "_pause", "_seek", "_pb_type", "start_time", "end_time", "lesson_id", "playback_minutes"]
    if all(col in data.columns for col in required_columns):
        # Calculate Scores
        scores = calculate_scores(data)
        st.write("Calculated Scores:")
        st.dataframe(scores)

        # Download Button
        csv = scores.to_csv(index=False)
        st.download_button("Download Scored Data", csv, "scores.csv", "text/csv")
    else:
        st.error(f"Missing columns. Ensure the dataset includes: {', '.join(required_columns)}")
