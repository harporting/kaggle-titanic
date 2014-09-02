""" 
Kaggle Titanic competition

Adapted from myfirstforest.py comitted by @AstroDave 
"""
import pandas as pd
import numpy as np
import time
import csv as csv
import re
from sklearn.grid_search import RandomizedSearchCV
from sklearn.svm import LinearSVC
from scipy.stats import randint as sp_randint
from operator import itemgetter


# Globals
############################3
ports_dict = {}               # Holds the possible values of 'Embarked' variable

cabinletter_matcher = re.compile("([a-zA-Z]+)")
cabinnumber_matcher = re.compile("([0-9]+)")



# Functions
############################

### This method will transform the raw data into the features that the model will operate on
def munge(df):     
    # Gender => 'Female' = 0, 'Male' = 1
    df['Gender'] = df['Sex'].map( {'female': 0, 'male': 1} ).astype(int)
 
    # Embarked => Four classes - 'C', 'Q', 'S', and NULL (create a separate class for unknown)
    if len(df.Embarked[ df.Embarked.isnull() ]) > 0:
        df.Embarked[ df.Embarked.isnull() ] = 'U'
 
    ports_dict = getPorts(df)
    df.Embarked = df.Embarked.map( lambda x: ports_dict[x]).astype(int)     # Convert all Embark strings to int


    # AgeClass => Six classes = Unknown(?), Baby(<3), Child(3-12), Teen(13-18), Adult(19-64), Senior(>65)
    df['AgeClass'] = df['Age'].map( lambda x : getAgeClass(x) )


    # Age => continuous value and missing values are replaced with median value
    median_age = df['Age'].dropna().median()
    if len(df.Age[ df.Age.isnull() ]) > 0:
        df.loc[ (df.Age.isnull()), 'Age'] = median_age


    # Fare => 
    if len(df.Fare[ df.Fare.isnull() ]) > 0:
        median_fare = np.zeros(3)
        for f in range(0,3):                                              # loop 0 to 2
            median_fare[f] = df[ df.Pclass == f+1 ]['Fare'].dropna().median()
        for f in range(0,3):                                              # loop 0 to 2
            df.loc[ (df.Fare.isnull()) & (df.Pclass == f+1 ), 'Fare'] = median_fare[f]
    
    # Cabin =>
    df['Cabin'][df.Cabin.isnull()] = 'U0'
    df['CabinLetter'] = df['Cabin'].map( lambda x : getCabinLetter(x))
    df['CabinNumber'] = df['Cabin'].map( lambda x : getCabinNumber(x))
    
    return df


### Simple method to split passengers into typical age groups
def getAgeClass(age):
    if np.isnan(age):
        return 0
    elif age < 3:
        return 1
    elif age < 13:
        return 2
    elif age < 19:
        return 3
    elif age < 65:
        return 4
    else:
        return 5


### This method will generate and/or return the dictionary of possible values of 'Embarked' => index for each value
def getPorts(df):
    global ports_dict
    
    if len(ports_dict) == 0:
        # determine distinct values of 'Embarked' variable
        ports = list(enumerate(np.unique(df['Embarked'])))
        # set the global dictionary
        ports_dict = { name : i for i, name in ports }
    
    return ports_dict

#==================================================================================================================
### Find the letter component of the cabin variable) 
def getCabinLetter(cabin):
    match = cabinletter_matcher.search(cabin)
    if match:
        return ord(match.group())
    else:
        return 'U'
 
### Find the number component of the cabin variable) 
def getCabinNumber(cabin):
    match = cabinnumber_matcher.search(cabin)
    if match:
        return float(match.group())
    else:
        return 0




# Script
###################################

# read in the training and testing data into Pandas.DataFrame objects
input_df = pd.read_csv('data/raw/train.csv', header=0)
test_df  = pd.read_csv('data/raw/test.csv',  header=0)

# data cleanup
input_df = munge(input_df)
test_df  = munge(test_df)

# Collect the test data's PassengerIds
ids = test_df['PassengerId'].values

# Remove variables that we couldn't transform into features:
input_df = input_df.drop(['Name', 'Sex', 'Ticket', 'Cabin', 'PassengerId'], axis=1) 
test_df  = test_df.drop(['Name', 'Sex', 'Ticket', 'Cabin', 'PassengerId'], axis=1) 

print 'Building Linear SVC with ' + str(len(input_df.columns)) \
      + ' columns: ' + str(list(input_df.columns.values))
    
print "Number of training examples: " + str(input_df.shape[0])

train_data = input_df.values
test_data = test_df.values

# Utility function to report optimal parameters
def report(grid_scores, n_top=3):
    params = None
    
    top_scores = sorted(grid_scores, key=itemgetter(1), reverse=True)[:n_top]
    for i, score in enumerate(top_scores):
        print("Model with rank: {0}".format(i + 1))
        print("Mean validation score: {0:.3f} (std: {1:.3f})".format(
              score.mean_validation_score,
              np.std(score.cv_validation_scores)))
        print("Parameters: {0}".format(score.parameters))
        print("")
        
        if params == None:
            params = score.parameters
    
    return params
    

# specify model parameters and distributions to sample from
params = {"dual": [False],
          "C": [0.01, 0.1, 0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0],
          #"loss": ["l1", "l2"],
          "penalty": ["l1", "l2"]}

# run randomized search to find the optimal parameters
n_iter_search = 30
lsvc = LinearSVC()
random_search = RandomizedSearchCV(lsvc, param_distributions=params, n_iter=n_iter_search)
random_search.fit(train_data[0::,1::], train_data[0::,0])
best_params = report(random_search.grid_scores_)

 
# Using the optimal parameters, predict the survival of the test set
print 'Predicting...'
lsvc = LinearSVC(**best_params)
lsvc.fit(train_data[0::,1::], train_data[0::,0])
#confidence = lsvc.decision_function(train_data[0::, 1::])
lsvc.predict(test_data)
output = lsvc.predict(test_data).astype(int)
 
# write results
predictions_file = open("data/results/linearsvc" + str(int(time.time())) + ".csv", "wb")
open_file_object = csv.writer(predictions_file)
open_file_object.writerow(["PassengerId","Survived"])
open_file_object.writerows(zip(ids, output))
predictions_file.close()
print 'Done.'