from nturl2path import url2pathname
from googleapiclient.discovery import build
import json
import pandas as pd
import streamlit as st
from PIL import Image

with open('secret.json') as f:
    secret = json.load(f)

YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
DEVELOPER_KEY = secret['KEY']

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

def video_search(youtube, q, max_results):
    response = youtube.search().list(
        q=q,
        part='id,snippet',
        order='relevance',
        type='video',
        maxResults=max_results
    ).execute()

    items_id = []
    items = response['items']
    for item in items:
        item_id = {}
        item_id['video_id'] = item['id']['videoId']
        item_id['channel_id'] = item['snippet']['channelId']
        item_id['thumbnails'] = item['snippet']['thumbnails']['high']['url']
        items_id.append(item_id)

    df_video = pd.DataFrame(items_id)
    return df_video

def get_results(df_video, threshold, viewdata):

    channel_ids = df_video['channel_id'].unique().tolist()

    subscriber_list = youtube.channels().list(
        id = ','.join(channel_ids),
        part='statistics',
        fields='items(id,statistics(subscriberCount))'
    ).execute()

    subscribers = []
    for item in subscriber_list['items']:
        subscriber = {}
        if len(item['statistics']) > 0:
            subscriber['channel_id'] = item['id']
            subscriber['subscriber_count'] = int(item['statistics']['subscriberCount'])
        else:
            subscriber['channel_id'] = item['id']
        subscribers.append(subscriber)

    df_subscribers = pd.DataFrame(subscribers)

    df = pd.merge(left=df_video, right=df_subscribers, on='channel_id')

    df_extracted = df[df['subscriber_count'] < threshold]

    video_ids = df_extracted['video_id'].tolist()
    videos_list = youtube.videos().list(
        id = ','.join(video_ids),
        # part='snippet,statistics',
        # fields='items(id,snippet(title),statistics(viewCount))'
        part='snippet,contentDetails,statistics',
        fields='items(id,snippet(title,publishedAt),contentDetails(duration),statistics(viewCount))'
    ).execute()

    videos_info = []
    items = videos_list['items']
    print('itmes')
    print(items)
    for item in items:
        video_info = {}
        video_info['video_id'] = item['id']
        video_info['title'] = item['snippet']['title']
        video_info['view_count'] = item['statistics']['viewCount']
        view_count = int(video_info['view_count'])
        if view_count < viewdata:
            videos_info.append(video_info)
    df_vieos_info = pd.DataFrame(videos_info)
    # st.image("https://static.streamlit.io/examples/cat.jpg", use_column_width=True)

    try:
        print(df_extracted)
        print(df_vieos_info)
        results = pd.merge(left=df_extracted, right=df_vieos_info, on ='video_id')
        images = results['thumbnails']
        results = results.loc[:,['video_id', 'title', 'view_count', 'subscriber_count', 'channel_id', 'thumbnails']]

    except:
        results = pd.DataFrame()
    return results, images

st.title('Youtube分析アプリ')
st.sidebar.write('## クエリと閾値の設定')
st.sidebar.write('### クエリの入力')
query = st.sidebar.text_input('検索クエリを入力してください', 'before:2013-03-30 after:2013-02-01 intitle:just dance')

st.sidebar.write('### 閾値の設定')
threshold = st.sidebar.slider('登録者数の閾値', 100, 10000, 500)

viewdata = st.sidebar.slider('再生数の閾値', 1, 10000, 500)

st.write('### 選択中のパラメータ')
st.markdown(f"""
- 検索クエリ：{query}
- 登録者数の閾値：{threshold}
- 再生数：{viewdata}
""")

df_video = video_search(youtube, q=query, max_results=50)
results, images = get_results(df_video, threshold, viewdata)
for img in images:
    st.image(img, use_column_width=True)


st.write('### 分析結果', results)
st.write('### 動画再生')

video_id = st.text_input('動画IDを入力してください')
url = f'https://youtu.be/{video_id}'

video_field = st.empty()
video_field.write('こちらに動画が表示されます')

if st.button('ビデオ表示'):
    if len(video_id) > 0:
        try:
            video_field.video(url)
        except:
            st.error('おっと！何かエラーが起きているようです。')
