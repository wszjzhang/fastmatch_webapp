import pickle
import sys
import re
import psycopg2

import pandas as pd
import numpy as np
import sqlalchemy as sa
from sqlalchemy_utils import database_exists, create_database

import requests
from bs4 import BeautifulSoup

import seaborn as sns
sns.set_context('talk')
sns.set_style('darkgrid') 
pd.set_option('display.max_columns', 500)
local_weave_pair = sa.create_engine("postgres://%s@localhost/%s"%('jiongz','weave_pair'))

import sexmachine.detector as gender
identify_gender = gender.Detector()

from sklearn.externals import joblib

def matches(user_name, user_degree, user_start_yr, looking_for):
    new_user_feature = get_new_user_info(user_name, user_degree, user_start_yr, looking_for)
    user_features = read_user_features()[:500]
    user_features = user_features[user_features['start_yr'].notnull()]
    meeting_features = meeting_feature_for_newuser(new_user_feature, user_features)

    match_result = predic_5star(meeting_features).sort('star_prob', ascending=False)

    return (int(match_result.iloc[0]['user_id']),
            int(match_result.iloc[1]['user_id']),
            int(match_result.iloc[2]['user_id']),
            int(match_result.iloc[3]['user_id']),
            int(match_result.iloc[4]['user_id']))

def read_user_features():
    ## create a database (if it doesn't exist)
    if not database_exists(local_weave_pair.url):
        create_database(local_weave_pair.url)
    print(database_exists(local_weave_pair.url))
    # connect:
    con = psycopg2.connect(database = 'weave_pair', user = 'jiongz')
    # query:
    sql_query = """
    SELECT * FROM user_features_combine;
    """
    user_features = pd.read_sql_query(sql_query,con)    
    return user_features


def get_new_user_info(user_name, user_degree, user_start_yr, looking_for):
    new_user_info = [user_name, user_degree, user_start_yr, looking_for]
    new_user_info_df = pd.DataFrame([new_user_info], columns = ['name', 'degree', 'start_yr', 'looking_for'])
    return new_user_info_df

def meeting_feature_for_newuser(new_user_feature, user_features):
    #new_user_feature = get_new_user_info(user_name, user_degree, user_start_yr, looking_for)
    #user_features = read_user_features()[:100]
    
    match_scores = []
    match_degrees = []
    degree_dict = {'b':1, 'm':2, 'p':3}
    match_yrs = []
    match_genders = []
    gender_dict = {'female':0, 'mostly_female':0, 'male':1, 'mostly_male':1, 'andy':2}
    meeting_times_y = []    
    #new user info
    get_ratings_mean = [4]*len(user_features)
    user_degrees = [degree_dict[new_user_feature['degree'].values[0][0].lower()]]*len(user_features)
    user_yrs = [new_user_feature['start_yr'].values[0]]*len(user_features)
    user_genders = [gender_dict[identify_gender.get_gender(new_user_feature['name'].values[0].split()[0])]]*len(user_features)
    user_meeting_times = [1]*len(user_features)

    for index,row in user_features.iterrows():
        # calculate match score
        demands = set(new_user_feature['looking_for'].values[0].split())
        supplies = set(row['title'].split())
        if not demands:
            match_scores.append(1)
        else:
            if demands.intersection(supplies):
                match_scores.append(2)
            else:
                match_scores.append(0)
    
        # get degree
        if row['degree']:
            match_degree = row['degree'][0].lower()
            if match_degree in degree_dict:
                match_degrees.append(degree_dict[match_degree])
            else:
                match_degrees.append(0)
        else:
            match_degrees.append(0)
        
    
        # get gender
        match_name = row['name'].split()[0]
        match_genders.append(gender_dict[identify_gender.get_gender(match_name)])
        
    #build meeting feature data frame
    feedback_dataset = user_features[['user_id', 'meeting_times', 'start_yr']].copy()
    feedback_dataset['get_rating_mean'] = pd.Series(np.array(get_ratings_mean), index=feedback_dataset.index)
    feedback_dataset['match_scores'] = pd.Series(np.array(match_scores), index=feedback_dataset.index)
    feedback_dataset['user_degrees'] = pd.Series(np.array(user_degrees), index=feedback_dataset.index)
    feedback_dataset['match_degrees'] = pd.Series(np.array(match_degrees), index=feedback_dataset.index)
    feedback_dataset['user_yrs'] = pd.Series(np.array(user_yrs), index=feedback_dataset.index)
    feedback_dataset['user_genders'] = pd.Series(np.array(user_genders), index=feedback_dataset.index)
    feedback_dataset['match_genders'] = pd.Series(np.array(match_genders), index=feedback_dataset.index)
    feedback_dataset['meeting_times_x'] = pd.Series(np.array(user_meeting_times), index=feedback_dataset.index)
    feedback_dataset = feedback_dataset[['user_id', 'meeting_times_x', 'meeting_times', 'get_rating_mean', 'match_scores', 'user_degrees', 'match_degrees', 'user_yrs', 'start_yr', 'user_genders', 'match_genders']]

    return feedback_dataset


def predic_5star(meeting_features):        
    #meeting_features = meeting_feature_for_newuser()
    clf = joblib.load('/Users/jiongz/jiong/projects/0_insight/6_webapp/app/static/rate_meeting.pkl')
    X = meeting_features[['meeting_times_x', 'meeting_times', 'get_rating_mean', 'match_scores', 'user_degrees', 'match_degrees', 'user_yrs', 'start_yr', 'user_genders', 'match_genders']].values.astype(float)
    y = clf.predict_proba(X)[:, -1]
    result = meeting_features[['user_id']].copy()
    result['star_prob'] = pd.Series(y, index=result.index)
    return result
    
