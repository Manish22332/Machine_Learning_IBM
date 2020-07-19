# -*- coding: utf-8 -*-
"""
Created on Fri Jun 26 21:26:35 2020

@author: Admin
"""

import numpy as np 
import pandas as pd 
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score
from math import sqrt
import warnings
warnings.filterwarnings('ignore')
#%matplotlib inline

# Reading and transforming the file
cities = pd.read_csv('D:/Projects/GlobalLandTemperaturesByCity.csv')
mumbai = cities.loc[cities['City'] == 'Bombay', ['dt','AverageTemperature']]
mumbai.columns = ['Date','Temp']
mumbai['Date'] = pd.to_datetime(mumbai['Date'])
mumbai.reset_index(drop=True, inplace=True)
mumbai.set_index('Date', inplace=True)

#I'm going to consider the temperature just from 1900 until the end of 2012
mumbai = mumbai.loc['1900':'2013-01-01']
mumbai = mumbai.asfreq('M', method='bfill')
mumbai.head()

plt.figure(figsize=(22,6))
sns.lineplot(x=mumbai.index, y=mumbai['Temp'])
plt.title('Temperature Variation in Mumbai from 1900 until 2012')
plt.show()

# i'm going to create a pivot table to plot the monthly temperatures through the years
mumbai['month'] = mumbai.index.month
mumbai['year'] = mumbai.index.year
pivot = pd.pivot_table(mumbai, values='Temp', index='month', columns='year', aggfunc='mean')
pivot.plot(figsize=(20,6))
plt.title('Yearly Mumbai temperatures')
plt.xlabel('Months')
plt.ylabel('Temperatures')
plt.xticks([x for x in range(1,13)])
plt.legend().remove()
plt.show()


year_avg = pd.pivot_table(mumbai, values='Temp', index='year', aggfunc='mean')
year_avg['10 Years MA'] = year_avg['Temp'].rolling(10).mean()
year_avg[['Temp','10 Years MA']].plot(figsize=(20,6))
plt.title('Yearly AVG Temperatures in Mumbai')
plt.xlabel('Year')
plt.ylabel('Temperature')
plt.xticks([x for x in range(1900,2012,5)])
plt.show()

train = mumbai[:-60].copy()
val = mumbai[-60:-12].copy()
test = mumbai[-12:].copy()

baseline = val['Temp'].shift()
baseline.dropna(inplace=True)
baseline.head()

def measure_rmse(y_true, y_pred):
    return sqrt(mean_squared_error(y_true,y_pred))

# Using the function with the baseline values
rmse_base = measure_rmse(val.iloc[1:,0],baseline)
print(f'The RMSE of the baseline that we will try to diminish is {round(rmse_base,4)} celsius degrees')

def check_stationarity(y, lags_plots=48, figsize=(22,8)):
    "Use Series as parameter"
    
    # Creating plots of the DF
    y = pd.Series(y)
    fig = plt.figure()

    ax1 = plt.subplot2grid((3, 3), (0, 0), colspan=2)
    ax2 = plt.subplot2grid((3, 3), (1, 0))
    ax3 = plt.subplot2grid((3, 3), (1, 1))
    ax4 = plt.subplot2grid((3, 3), (2, 0), colspan=2)

    y.plot(ax=ax1, figsize=figsize)
    ax1.set_title('Mumbai Temperature Variation')
    plot_acf(y, lags=lags_plots, zero=False, ax=ax2);
    plot_pacf(y, lags=lags_plots, zero=False, ax=ax3);
    sns.distplot(y, bins=int(sqrt(len(y))), ax=ax4)
    ax4.set_title('Distribution Chart')

    plt.tight_layout()
    
    print('Results of Dickey-Fuller Test:')
    adfinput = adfuller(y)
    adftest = pd.Series(adfinput[0:4], index=['Test Statistic','p-value','Lags Used','Number of Observations Used'])
    adftest = round(adftest,4)
    
    for key, value in adfinput[4].items():
        adftest["Critical Value (%s)"%key] = value.round(4)
        
    print(adftest)
    
    if adftest[0].round(2) < adftest[5].round(2):
        print('\nThe Test Statistics is lower than the Critical Value of 5%.\nThe serie seems to be stationary')
    else:
        print("\nThe Test Statistics is higher than the Critical Value of 5%.\nThe serie isn't stationary")
        
# The first approach is to check the series without any transformation
check_stationarity(train['Temp'])

check_stationarity(train['Temp'].diff(12).dropna())


def walk_forward(training_set, validation_set, params):
    '''
    Params: it's a tuple where you put together the following SARIMA parameters: ((pdq), (PDQS), trend)
    '''
    history = [x for x in training_set.values]
    prediction = list()
    
    # Using the SARIMA parameters and fitting the data
    pdq, PDQS, trend = params

    #Forecasting one period ahead in the validation set
    for week in range(len(validation_set)):
        model = sm.tsa.statespace.SARIMAX(history, order=pdq, seasonal_order=PDQS, trend=trend)
        result = model.fit(disp=False)
        yhat = result.predict(start=len(history), end=len(history))
        prediction.append(yhat[0])
        history.append(validation_set[week])
        
    return prediction


# Let's test it in the validation set
val['Pred'] = walk_forward(train['Temp'], val['Temp'], ((3,0,0),(0,1,1,12),'c'))

# Measuring the error of the prediction
rmse_pred = measure_rmse(val['Temp'], val['Pred'])

print(f"The RMSE of the SARIMA(3,0,0),(0,1,1,12),'c' model was {round(rmse_pred,4)} celsius degrees")
print(f"It's a decrease of {round((rmse_pred/rmse_base-1)*100,2)}% in the RMSE")

# Creating the error column
val['Error'] = val['Temp'] - val['Pred']

def plot_error(data, figsize=(20,8)):
    '''
    There must have 3 columns following this order: Temperature, Prediction, Error
    '''
    plt.figure(figsize=figsize)
    ax1 = plt.subplot2grid((2,2), (0,0))
    ax2 = plt.subplot2grid((2,2), (0,1))
    ax3 = plt.subplot2grid((2,2), (1,0))
    ax4 = plt.subplot2grid((2,2), (1,1))
    
    #Plotting the Current and Predicted values
    ax1.plot(data.iloc[:,0:2])
    ax1.legend(['Real','Pred'])
    ax1.set_title('Current and Predicted Values')
    
    # Residual vs Predicted values
    ax2.scatter(data.iloc[:,1], data.iloc[:,2])
    ax2.set_xlabel('Predicted Values')
    ax2.set_ylabel('Errors')
    ax2.set_title('Errors versus Predicted Values')
    
    ## QQ Plot of the residual
    sm.graphics.qqplot(data.iloc[:,2], line='r', ax=ax3)
    
    # Autocorrelation plot of the residual
    plot_acf(data.iloc[:,2], lags=(len(data.iloc[:,2])-1),zero=False, ax=ax4)
    plt.tight_layout()
    plt.show()
    
    
# We need to remove some columns to plot the charts
val.drop(['month','year'], axis=1, inplace=True)
val.head()

plot_error(val)

#Creating the new concatenating the training and validation set:
future = pd.concat([train['Temp'], val['Temp']])
future.head()


# Using the same parameters of the fitted model
model = sm.tsa.statespace.SARIMAX(future, order=(3,0,0), seasonal_order=(0,1,1,12), trend='c')
result = model.fit(disp=False)


test['Pred'] = result.predict(start=(len(future)), end=(len(future)+13))

test[['Temp', 'Pred']].plot(figsize=(22,6))
plt.title('Current Values compared to the Extrapolated Ones')
plt.show()

test_baseline = test['Temp'].shift()

test_baseline[0] = test['Temp'][0]

rmse_test_base = measure_rmse(test['Temp'],test_baseline)
rmse_test_extrap = measure_rmse(test['Temp'], test['Pred'])

print(f'The baseline RMSE for the test baseline was {round(rmse_test_base,2)} celsius degrees')
print(f'The baseline RMSE for the test extrapolation was {round(rmse_test_extrap,2)} celsius degrees')
print(f'That is an improvement of {-round((rmse_test_extrap/rmse_test_base-1)*100,2)}%')

#
mod = sm.tsa.statespace.SARIMAX(train['Temp'], trend='c', order=(1,1,1), seasonal_order=(0,1,1,12))
res = mod.fit(disp=False)
val['pred1'] = res.predict()
val[['Temp', 'pred1']].plot(figsize=(22,6))
plt.title('Current Values compared to the Extrapolated Ones')
plt.show()
r2_score(val['pred1'], val['Temp'])
r2_score(val['Pred'], val['Temp'])
test['pred2'] = res.predict(start=test.index[0], end=test.index[-1])
val['pred3'] = res.predict(start=val.index[0], end=val.index[-1])
r2_score(val['pred3'], val['Temp'])
test['pred2'] = res.predict(start=test.index[0], end=test.index[-1])
r2_score(test['pred2'], test['Temp'])
r2_score(test['Pred'], test['Temp'])

print(res.summary())
print(result.summary())





