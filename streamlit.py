from regex import D
import tweepy
from textblob import TextBlob
import preprocessor as p
import statistics
from typing import List
import streamlit as st
import streamlit.components.v1 as components
import requests
import plotly.figure_factory as ff
import plotly.express as px
import numpy as np
import pandas as pd
import random
from github import Github
import datetime

bearer_token = st.secrets["bearer_token"]
github_token = st.secrets["github_token"]

client = tweepy.Client(bearer_token)

def get_tweets(keyword: str) -> List[str]:
    all_tweets = []
    for tweet in client.search_recent_tweets(query=keyword + " lang:en -is:retweet", max_results=100).data:
        all_tweets.append(tweet)

    return all_tweets

def clean_tweets(all_tweets: List[str]) -> List[str]:
    tweets_clean = []
    for tweet in all_tweets:
        tweets_clean.append(p.clean(str(tweet)))
    tweets_id = []
    for tweet in all_tweets:
        tweets_id.append(tweet.id)    

    return tweets_clean, tweets_id

def get_sentiment(all_tweets: List[str]) -> List[float]:
    sentiment_scores = []
    subjectivity_scores = []
    for tweet in all_tweets:
        blob = TextBlob(tweet)
        sentiment_scores.append(blob.sentiment.polarity)
        subjectivity_scores.append(blob.sentiment.subjectivity)

    return sentiment_scores, subjectivity_scores

def generate_average_sentiment_score(keyword: str) -> int:
    tweets = get_tweets(keyword)
    tweets_clean, tweets_id = clean_tweets(tweets)
    sentiment_scores, subjectivity_scores = get_sentiment(tweets_clean)
    average_score = statistics.mean(sentiment_scores)
    sorted_tweets = [x for _, x in sorted(zip(sentiment_scores, tweets_id))]

    return average_score, sorted_tweets, sentiment_scores, subjectivity_scores

st.set_page_config(
     page_title="What does humanity prefer?",
     layout="wide",
 )

def theTweet(tweet_url):
    api = "https://publish.twitter.com/oembed?url={}".format(tweet_url)
    response = requests.get(api)
    res = response.json()["html"]
    return res

def random_keywords():
    g = Github(github_token)
    user = g.get_user()
    repo = g.get_repo(user.login + '/streamlit_twitter')
    file = repo.get_contents('example_keywords.txt', ref='master')
    pairs = (file.decoded_content.decode('utf-8')).split('\n')
    random_pair = (pairs[random.randrange(0, len(pairs)-1)])
    keywords = random_pair.split('\ ')
    st.session_state.keyword1 = keywords[0]
    st.session_state.keyword2 = keywords[1]
    return keywords


def update_keywords(keyword1, keyword2):
    g = Github(github_token)
    user = g.get_user()
    repo = g.get_repo(user.login + '/streamlit_twitter')
    file = repo.get_contents('searched_keywords.txt', ref='master')
    file_path = file.path
    updated_file = (file.decoded_content).decode('utf-8') + keyword1 + '\ ' + keyword2 + '\ ' + str(datetime.datetime.now()) + '\n'
    repo.update_file(file_path, 'Keywords update.', updated_file, file.sha, branch='master')

if 'keyword1' not in st.session_state:
    st.session_state.keyword1 = ""
if 'keyword2' not in st.session_state:
    st.session_state.keyword2 = ""

st.header("What does humanity prefer?")
col1, col2 = st.columns(2)

first_thing = col1.text_input("Enter first thing", st.session_state.keyword1)
second_thing = col2.text_input("Enter second thing", st.session_state.keyword2)
check_button = col1.button("Check!")
lucky_button = col2.button("Feeling lucky!", on_click = random_keywords)

if check_button:
    first_score, first_tweets, first_sentiment_scores, first_subjectivity_scores = generate_average_sentiment_score(first_thing)
    second_score, second_tweets, second_sentiment_scores, second_subjectivity_scores = generate_average_sentiment_score(second_thing)
    if(len(first_sentiment_scores)<90):
        st.empty()
        st.header(f"We've found too few tweets about {first_thing}! Try another keyword.")
    elif(len(second_sentiment_scores)<90):
        st.empty()
        st.header(f"We've found too few tweets about {second_thing}! Try another keyword.")
    else:
        if (first_score > second_score):
            winner = first_thing
            looser = second_thing
            winner_tweets = first_tweets
            looser_tweets = second_tweets
        else:
            winner = second_thing
            looser = first_thing
            winner_tweets = second_tweets
            looser_tweets = first_tweets

        update_keywords(first_thing, second_thing)

        st.empty()
        st.header(f"The humanity prefers {winner} over {looser}!")

        example_tweets = 4
        winner_res = []
        looser_res = []
        for x in range(example_tweets):
            winner_res.append(theTweet('https://twitter.com/twitter/statuses/' + str(winner_tweets[-x-1]))) 
            looser_res.append(theTweet('https://twitter.com/twitter/statuses/' + str(looser_tweets[x])))
    
        col3, col4 = st.columns(2)
        with col3:
            st.subheader("About " + winner + "... :heart_eyes:")
            for x in range(example_tweets):
                components.html(winner_res[x], height=700, scrolling=True)
        with col4:
            st.subheader("About " + looser + "... :rage:")
            for x in range(example_tweets):
                components.html(looser_res[x], height=700, scrolling=True)

        hist_data = [first_sentiment_scores, second_sentiment_scores]
        group_labels = [first_thing, second_thing]
        fig1 = ff.create_distplot(hist_data, group_labels, bin_size=[.1, .1])
        st.plotly_chart(fig1, use_container_width=True)

        df1 = pd.DataFrame(data={"polarity": first_sentiment_scores, "subjectivity": first_subjectivity_scores, "keyword": first_thing})
        df2 = pd.DataFrame(data={"polarity": second_sentiment_scores, "subjectivity": second_subjectivity_scores, "keyword": second_thing})
        df = pd.concat([df1, df2], axis=0)
        fig2 = px.scatter(df, x='polarity', y='subjectivity', color='keyword', size='subjectivity')
        st.plotly_chart(fig2, use_container_width=True) 
