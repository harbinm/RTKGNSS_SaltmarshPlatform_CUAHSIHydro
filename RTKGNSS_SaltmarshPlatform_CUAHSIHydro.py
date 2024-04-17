#This code serves the purpose of processing .csv RW5 files created by the Carlson Report Generator
#and .xlsx files created by the Omega Digital Transducer Application

#Created for the fulfillment of the CUAHSI Hydroinformatics Innovation Fellowship
#by Morgan Harbin
#Embry-Riddle Aeronautical University Department of Civil Engineering
#Environmental Sustainability and Resilience Program

#NOTE: before importing .rw5 file,
#use the Carlson converter tool to produce a .csv version of your raw .rw5
#Carlson Report Generator: http://www.carlsonemea.com/cwa/report/index.php?lang=RO

surface = 'Sand(soft)'#Single-word string describing surface
location = 'Ormond'  #Single-word string describing location

rw5_files = ['CUAHSI_Ormond1.rw5.csv', 'CUAHSI_Ormond2.rw5.csv', 'CUAHSI_Ormond3.rw5.csv', 'CUAHSI_Ormond4.rw5.csv'] #List of files containing elevation data converted from raw (.rw5) format to comma-separated values (.csv) format#List of files containing elevation data converted from raw (.rw5) format to comma-separated values (.csv) format
INUSBH_files = ['CUAHSI_Ormond1.xlsx', 'CUAHSI_Ormond2.xlsx', 'CUAHSI_Ormond3.xlsx', 'CUAHSI_Ormond4.xlsx'] #List of .xlsx files containing applied pressure data

load_delta_values = [] #Initiate list to contain values of change in load

Z_delta_values = [] #Initiate list to contain values of change in elevation

area_toposhoe = 2.95 #Floating point surface area of topo shoe; to be used to convert load to pressure

#-------------------------

#Import necessary libraries

import pandas as pd
import requests
import matplotlib.pyplot as plt
import numpy as np
import urllib.request as url
from urllib.request import urlopen
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter
from datetime import datetime
from datetime import date
import math
from scipy.signal import butter, filtfilt
from pandas import Timestamp

from matplotlib.lines import Line2D # for the legend
from sklearn.linear_model import LinearRegression

!pip install matplotlib-label-lines
import matplotlib.pyplot as plt
from labellines import labelLines

#-------------------------

#Define filtering functions to be used later for data analysis

def butter_lowpass(cutoff, fs, order=5):
  from scipy.signal import butter, filtfilt
  nyq = 0.5 * fs
  normal_cutoff = cutoff / nyq
  b, a = butter(order, normal_cutoff, btype='low', analog=False)
  return b, a

def butter_lowpass_filtfilt(data, cutoff, fs, order=5):
  from scipy.signal import butter, filtfilt
  b, a = butter_lowpass(cutoff, fs, order=order) #Use previously defined Butterworth filter
  y = filtfilt(b, a, data)
  return y

#Butterworth filter code can be found here: https://stackoverflow.com/questions/28536191/how-to-filter-smooth-with-scipy-numpy
#Butterworth filter has a propensity to flatten data; this is useful for a first round of filtration, but it does not represent data well
#Future research: consider performing a first round of butterworth filtration, but then perform a second round with a more representative filter


def to_integer(dt_time): 
    return 10000*dt_time.year + 100*dt_time.month + dt_time.day

#Function code can be found here: https://stackoverflow.com/questions/28154066/how-to-convert-datetime-to-integer-in-python

def take_closest(myList, myNumber):

  from bisect import bisect_left

  pos = bisect_left(myList, myNumber)
  if pos == 0:
      return myList[0]
  if pos == len(myList):
      return myList[-1]
  before = myList[pos - 1]
  after = myList[pos]
  if after - myNumber < myNumber - before:
    return after
  else:
      return before

#Function code can be found here: https://stackoverflow.com/questions/12141150/from-list-of-integers-get-number-closest-to-a-given-value

def printTable(myDict, colList=None, sep='\uFFFA'):
   """ Pretty print a list of dictionaries (myDict) as a dynamically sized table.
   If column names (colList) aren't specified, they will show in random order.
   sep: row separator. Ex: sep='\n' on Linux. Default: dummy to not split line.
   Author: Thierry Husson - Use it as you want but don't blame me.
   """
   if not colList: colList = list(myDict[0].keys() if myDict else [])
   myList = [colList] # 1st row = header
   for item in myDict: myList.append([str(item[col] or '') for col in colList])
   colSize = [max(map(len,(sep.join(col)).split(sep))) for col in zip(*myList)]
   formatStr = ' | '.join(["{{:<{}}}".format(i) for i in colSize])
   line = formatStr.replace(' | ','-+-').format(*['-' * i for i in colSize])
   item=myList.pop(0); lineDone=False
   while myList or any(item):
      if all(not i for i in item):
         item=myList.pop(0)
         if line and (sep!='\uFFFA' or not lineDone): print(line); lineDone=True
      row = [i.split(sep,1) for i in item]
      print(formatStr.format(*[i[0] for i in row]))
      item = [i[1] if len(i)>1 else '' for i in row]

#Function code can be found here: https://stackoverflow.com/questions/17330139/python-printing-a-dictionary-as-a-horizontal-table-with-headers

#The following code was made specifically for this fellowship:
def smooth_and_slice(Load,TimeINUSBH): #smooth_and_slice uses a butterworth filter and slices data at every other point of slope inflection (i.e., cut into full "wavelengths")

#Output the following variables to be used throughout code:
  global Load_smooth
  global inflectionMidpoint
  global inflectionMidpointTrack
  global dictLoad
  global dictTimeINUSBH


  Load_smooth = butter_lowpass_filtfilt(Load, cutoff, fs); #Perform Butterworth filter function on Load data; new dataset is called Load_smooth

  sign = 1; #Use sign to track positive or negative slope (sign = 1 represents positive slope)
  inflection = []; #Initiate temporary list to track inflection points for each "wavelength" (i.e., points where slope transitions between positive or negative)
  inflectionMidpointTrack = [TimeINUSBH[0]]; #Initiate blank list to track every other "inflection" point; this inflectionMidpointTrack variable constitutes the true transition between survey instances; set the first time increment to define the first point of the first survey instance

  for i in range(0,len(Load)-1): #This loop scans each item in the Load input variable (use load_smooth for this) and determines whether it is a true inflectionMidpointTrack
    sign0 = sign;
    point1 = Load_smooth[i];
    point2 = Load_smooth[i+1];
    pointDiff = point2 - point1;

    if pointDiff < 0: #First determines if the differences between adjacent points is positive or negative, assignes "sign" value based on positivity of slope
      sign = 0;

    else:
      sign = 1;

    if sign != sign0: #If 2 consecutive points have slopes of different sign, define this as an inflection point
      inflection.append(TimeINUSBH[i]);

    if len(inflection) > 1: #Every other inflection value stored, find the midpoint between and define this as a break point between survey instances (inflectionMidpoint)
      delta = inflection[1] - inflection[0];
      inflectionMidpoint = inflection[1] + (delta/2);

      #Split dataset at inflectionMidpoint
      inflectionMidpointTrack.append(inflectionMidpoint); #Store these inflectionMidpoints in a list
      inflection = []; #Reset temporary inflection list

  inflectionMidpointTrack.append(TimeINUSBH[-1]); #After all loops are completed, be sure to add the final time value as a break point

#Following this, the overall time series will be broken into time series of individual survey instances
#Track Load, Elevation, and Time components of each instance using dictionaries:
  dictLoad = {}; 
  dictTimeINUSBH = {};

  for i in range(0, len(inflectionMidpointTrack)-1):
    #Define new list between inflection midpoints
    slice1 = take_closest(TimeINUSBH, inflectionMidpointTrack[i]);
    sliceIndex1 = TimeINUSBH.index(slice1);

    slice2 = take_closest(TimeINUSBH, inflectionMidpointTrack[i+1]);
    sliceIndex2 = TimeINUSBH.index(slice2);

    dictLoad['L' + str(i)] = Load[sliceIndex1:sliceIndex2]; #Create a new list within the dictLoad dictionary that represents all load values within a survey instance
    dictTimeINUSBH['T' + str(i)] = TimeINUSBH[sliceIndex1:sliceIndex2]; #Create a new list within the dictTimeINUSBH dictionary that represents all time values within a survey instance as reported by the Omega INUSBH

  return Load_smooth, inflectionMidpoint, inflectionMidpointTrack #Output new lists

figure_number = 1 #Initiate figure_number to be printed on the first figure

#For each file of Load and Elevation data, perform the following operations:
for file_ticker in range(0,len(rw5_files)): 

  sessionName = 'CUAHSI_' + surface + str(file_ticker) #Name the session with no spaces; to be used as output file name
  sessionTitle = 'CUAHSI ' + location + ': ' + surface + f' #{file_ticker}' #Title the session in plain English; to be used as figure header

  rw5fileName = rw5_files[file_ticker] #Identify current rw5_file
  INUSBHfileName = INUSBH_files[file_ticker] #Identify current INUSBH_file

  dict_load_delta_values = {} #Initiate blank dictionary storing delta values (i.e., change in load over a complete survey instance)
  dict_Z_delta_values = {} #Initiate blank dictionary storing elevation delta values (i.e., change in elevation over a complete survey instance)

  #Read imported .csv

  dfrw5 = pd.read_csv(rw5fileName)
  dfrw5 = dfrw5[dfrw5['GPS Time'].notna()]
  dfrw5 = dfrw5[dfrw5['GPS Date'].notna()]
  dfrw5 = dfrw5.reset_index()

  #Read imported .xlsx

  dfINUSBH = pd.read_excel(INUSBHfileName)

  # Translate Load dataframe data into list format:

  Load = [] #Blank "Load" list to be populated below

  for x in range(10,len(dfINUSBH['Unnamed: 1'])):
    Loadstring = -dfINUSBH['Unnamed: 1'][x] #Elevations indexed and converted to string format; INVERT compression data to be positive (hence negative sign)
    Load.append(Loadstring/area_toposhoe)

  #Identify range of survey session Load data  
  LoadMAX = max(Load)
  LoadMIN = min(Load)
  LoadRANGE = max(Load) - min(Load)

  # Translate Elevation dataframe data into list format:

  Z = [] #Blank "Z" list to be populated below

  for x in range(1,len(dfrw5['Local_Z'])): #for loop scans .csv column "Local_Z" and appends elevation values into empty "Z" list
    Zstring = dfrw5['Local_Z'][x] #Elevations indexed and converted to string format
    Z.append(Zstring)


  # Translate TimeINUSBH dataframe data into list format:

  TimeINUSBH = [] #Blank "Time" list to be populated below

  for x in range(10,len(dfINUSBH['IN-USBH - 617622'])):  #for loop scans .csv columns "GPS Time" and "GPS Date" and appends datetime values into empty "Time" list
    Timestring = str(dfINUSBH['IN-USBH - 617622'][x]) #Times indexed from Date and Time columns, converted to strings, and strung together in datetime readable format
    try:
      Timeobject = datetime.strptime(Timestring, '%Y-%m-%d %H:%M:%S.%f') #Times converted from string objects to datetime objects

    except:
      Timeobject = datetime.strptime(Timestring, '%Y-%m-%d %H:%M:%S')
    TimeINUSBH.append(Timeobject)

    
  # Translate Timerw5 dataframe data into list format:

  Timerw5 = [] #Blank "Time" list to be populated below

  for x in range(1,len(dfrw5['GPS Time'])):  #for loop scans .csv columns "GPS Time" and "GPS Date" and appends datetime values into empty "Time" list
    Timestring = str(dfrw5['GPS Date'][x]) + ' ' + str(dfrw5['GPS Time'][x]) #Times indexed from Date and Time columns, converted to strings, and strung together in datetime readable format
    Timeobject = datetime.strptime(Timestring, '%m-%d-%Y %H:%M:%S') #Times converted from string objects to datetime objects
    Timerw5.append(Timeobject)

#Define cutoff and fs values to be used to perform butter_lowpass_filtfilt; change these if necessary
  cutoff = 25
  fs = 50000

 #Plot time series

  fig, ax1 = plt.subplots(figsize=(20,10));

  ax1.plot(TimeINUSBH, Load, label="Applied Pressure Time Series", linestyle = '-', color = 'midnightblue');
  fig.autofmt_xdate();
  ax1.set_title(f'Elevation vs. Applied Pressure Time Series: {location} + {surface}\n', fontstyle = 'normal', fontsize = 17, weight = 'bold');
  ax1.set_ylabel('Applied Pressure (psi)', fontstyle = 'oblique');
  ax1.set_xlabel('\nTime', fontstyle = 'oblique');

  ax2 = ax1.twinx()

  ax2.plot(Timerw5, Z, label="Elevation Time Series", linestyle = '-', color= 'cornflowerblue');
  ax2.set_ylabel('RTK-GNSS Elevation (m)', fontstyle = 'oblique')


  fig.autofmt_xdate();
  fig.legend(bbox_to_anchor = (0.895,0.275));

  plt.savefig(f'{sessionName}_TimeSeries.png')

  smooth_and_slice(Load, TimeINUSBH);

  plt.plot(TimeINUSBH, Load_smooth, label= 'Smoothed Applied Pressure Time Series', linestyle = '-', color = 'midnightblue')
  plt.plot(TimeINUSBH, Load, linestyle = '--', label= 'Applied Pressure Time Series', color = 'cornflowerblue')

  plt.ylabel('Applied Pressure (psi)', fontstyle = 'oblique');
  plt.xlabel('\nTime', fontstyle = 'oblique');
  plt.legend(bbox_to_anchor = (1,0.15));

  for i in range(0,len(inflectionMidpointTrack)):
    plt.axvline(x = inflectionMidpointTrack[i], color = 'darkgrey')

  cutoff_Z = 2000
  fs_Z = 50000
  Z_smooth = butter_lowpass_filtfilt(Z, cutoff_Z, fs_Z);

  plt.plot(Timerw5, Z_smooth, label= 'Smoothed Elevation Time Series', linestyle = '-', color = 'midnightblue')
  plt.plot(Timerw5, Z, linestyle = '--', label= 'Elevation Time Series', color = 'cornflowerblue')

  plt.ylabel('Elevation (m)', fontstyle = 'oblique');
  plt.xlabel('\nTime', fontstyle = 'oblique');
  plt.legend(bbox_to_anchor = (1,0.15));

  for i in range(0,len(inflectionMidpointTrack)):
    plt.axvline(x = inflectionMidpointTrack[i], color = 'darkgrey')

  dictLoad_smooth = {}
  dictZ_smooth = {}
  dictZ = {}
  dictTimerw5 = {}

  for i in range(0, len(inflectionMidpointTrack)-1):
    #Define new list between inflection midpoints
    slice1 = take_closest(TimeINUSBH, inflectionMidpointTrack[i]);
    sliceIndex1 = TimeINUSBH.index(slice1);

    slice1_Z = take_closest(Timerw5, inflectionMidpointTrack[i]);
    sliceIndex1_Z = Timerw5.index(slice1_Z);

    slice2 = take_closest(TimeINUSBH, inflectionMidpointTrack[i+1]);
    sliceIndex2 = TimeINUSBH.index(slice2);

    slice2_Z = take_closest(Timerw5, inflectionMidpointTrack[i+1]);
    sliceIndex2_Z = Timerw5.index(slice2_Z);

    dictLoad_smooth['LS' + str(i)] = Load_smooth[sliceIndex1:sliceIndex2];
    dictZ['Z' + str(i)] = Z[sliceIndex1_Z:sliceIndex2_Z]
    dictZ_smooth['ZS' + str(i)] = Z_smooth[sliceIndex1_Z:sliceIndex2_Z];
    dictTimerw5['Trw5' + str(i)] = Timerw5[sliceIndex1_Z:sliceIndex2_Z];

  for i in range(0, len(dictTimerw5)):
    if i == 0:
      if dictTimerw5['Trw5' + str(i)] == []:
        placeHolder1 = dictTimerw5['Trw51'][0]
        placeHolder2 = dictZ['Z1'][0]
        placeHolder3 = dictZ_smooth['ZS1'][0]
        dictTimerw5['Trw50'] = [placeHolder1]
        dictZ['Z0'] = [placeHolder2]
        dictZ_smooth['ZS0'] = [placeHolder3]

    else:

      if dictTimerw5['Trw5' + str(i)] == []:
        placeHolder1 = dictTimerw5['Trw5' + str(i-1)][-1]
        placeHolder2 = dictZ['Z' + str(i-1)][-1]
        placeHolder3 = dictZ_smooth['ZS' + str(i-1)][-1]
        dictTimerw5['Trw5' + str(i)] = [placeHolder1]
        dictZ['Z' + str(i)] = [placeHolder2]
        dictZ_smooth['ZS' + str(i)] = [placeHolder3]

  for i in range(0, len(dictTimeINUSBH)):
    if i == 0:
      if dictTimeINUSBH['T' + str(i)] == []:
        placeHolder1 = dictTimeINUSBH['T1'][0]
        placeHolder2 = dictLoad['L1'][0]
        placeHolder3 = dictZ_smooth['LS1'][0]
        dictTimerw5['T0'] = [placeHolder1]
        dictLoad['L0'] = [placeHolder2]
        dictLoad_smooth['LS0'] = [placeHolder3]
    else:
      if dictTimeINUSBH['T' + str(i)] == []:
        placeHolder1 = dictTimeINUSBH['T' + str(i-1)][-1]
        placeHolder2 = dictLoad['L' + str(i-1)][-1]
        placeHolder3 = dictLoad_smooth['LS' + str(i-1)][-1]
        dictTimeINUSBH['T' + str(i)] = [placeHolder1]
        dictLoad['L' + str(i)] = [placeHolder2]
        dictLoad_smooth['LS' + str(i)] = [placeHolder3]

  dictTimeINUSBH_seconds = []
  dictTimerw5_seconds = []

  for i in range(0,len(dictTimeINUSBH)):
    dictTimeINUSBH_min = dictTimeINUSBH['T' + str(i)][0]
    dictTimeINUSBH_min_float = datetime.timestamp(dictTimeINUSBH_min)
    dictTimeINUSBH_max = dictTimeINUSBH['T' + str(i)][-1]
    dictTimeINUSBH_max_float = datetime.timestamp(dictTimeINUSBH_max)
    dictTimeINUSBH_range = dictTimeINUSBH_max - dictTimeINUSBH_min
    dictTimeINUSBH_range_float = dictTimeINUSBH_max_float - dictTimeINUSBH_min_float
    dictTimeINUSBH_seconds.append(dictTimeINUSBH_range_float)

    dictTimeINUSBH_current = dictTimeINUSBH['T' + str(i)]

    for n in range(0, len(dictTimeINUSBH_current)):
      dictTimeINUSBH['T' + str(i)][n] = datetime.timestamp(dictTimeINUSBH['T' + str(i)][n]) - dictTimeINUSBH_min_float

    dictTimerw5_min = dictTimerw5['Trw5' + str(i)][0]
    dictTimerw5_min_float = datetime.timestamp(dictTimerw5_min)
    dictTimerw5_max = dictTimerw5['Trw5' + str(i)][-1]
    dictTimerw5_max_float = datetime.timestamp(dictTimerw5_max)
    dictTimerw5_range = dictTimerw5_max - dictTimerw5_min
    dictTimerw5_range_float = dictTimerw5_max_float - dictTimerw5_min_float
    dictTimerw5_seconds.append(dictTimerw5_range_float)

    dictTimerw5_current = dictTimerw5['Trw5' + str(i)]

    for m in range(0, len(dictTimerw5_current)):
      dictTimerw5['Trw5' + str(i)][m] = datetime.timestamp(dictTimerw5['Trw5' + str(i)][m]) - dictTimerw5_min_float

  #Calculate derivatives:

  dictLoad_derivative = {}
  dictZ_derivative = {}

  for i in range(0, len(dictLoad_smooth)):

    dictIndexL_current = dictLoad_smooth['LS' + str(i)]

    listLoad_current = []

    for n in range(1, len(dictIndexL_current)):

      L_N = dictLoad_smooth['LS' + str(i)][n]
      L_Nm1 = dictLoad_smooth['LS' + str(i)][n-1]

      TL_N = dictTimeINUSBH['T' + str(i)][n]
      TL_Nm1 = dictTimeINUSBH['T' + str(i)][n-1]

      valueLoad_current = (L_N - L_Nm1)/(TL_N - TL_Nm1)
      listLoad_current.append(valueLoad_current)

    listLoad_current.append(valueLoad_current)
    dictLoad_derivative["L'" + str(i)] = listLoad_current


    dictIndexZ_current = dictZ_smooth['ZS' + str(i)]

    listZ_current = []

    if len(listZ_current) == 1:
      valueZ_current = listZ_current[0]

    if len(listZ_current) == 0:

      try:
       valueZ_current = dictZ_smooth['ZS' + str(i-1)][-1]

      except:
         valueZ_current = dictZ_smooth['ZS' + str(i+1)][0]

    for m in range(1,len(dictIndexZ_current)):
      Z_N = dictZ_smooth['ZS' + str(i)][m]
      Z_Nm1 = dictZ_smooth['ZS' + str(i)][m-1]

      TZ_N = dictTimerw5['Trw5' + str(i)][m]
      TZ_Nm1 = dictTimerw5['Trw5' + str(i)][m-1]

      valueZ_current = (Z_N - Z_Nm1)/(TZ_N - TZ_Nm1)
      listZ_current.append(valueZ_current)

    listZ_current.append(valueZ_current)
    dictZ_derivative["Z'" + str(i)] = listZ_current

  # loop through the length of tickers and keep track of index
  delLoadValues = []
  delZValues = []

  for n, listLoad in enumerate(dictLoad):
    figWidth = 3
    figHeight = 4*figWidth

    plt.figure(figsize=(figWidth, figHeight));

    # add a new subplot iteratively

    fig, (ax1, ax2) = plt.subplots(2);

    fig.subplots_adjust(hspace = 1.5);

    parax1 = ax1.twinx();

    ax1.plot(dictTimeINUSBH['T' + str(n)], dictLoad['L' + str(n)], linestyle = '', marker = '.', markersize = 0.75, color = 'palegoldenrod', label = 'Load');
    ax1.plot(dictTimeINUSBH['T' + str(n)], dictLoad_smooth['LS' + str(n)], linestyle = '-', linewidth = 0.5, color = 'goldenrod', label = 'Load (filtered)');
    ax1.plot(0,dictLoad_smooth['LS' + str(n)][0], linestyle = '-', linewidth = 0.5, color = 'papayawhip', label = 'Load (derivative)');
    parax1.plot(dictTimeINUSBH['T' + str(n)], dictLoad_derivative["L'" + str(n)], linestyle = '-', linewidth = 0.5, color = 'papayawhip', label = 'Load (derivative)');

    # ax[1] = ax.twinx()

    parax2 = ax2.twinx();

    ax2.plot(dictTimerw5['Trw5' + str(n)], dictZ['Z' + str(n)], linestyle = '', marker = '.', markersize = 0.75, color = 'steelblue', label = 'Elevation');
    ax2.plot(dictTimerw5['Trw5' + str(n)], dictZ_smooth['ZS' + str(n)], linestyle = '-', linewidth = 0.5, color = 'midnightblue', label = 'Elevation (filtered)');
    ax2.plot(0,dictZ_smooth['ZS' + str(n)][0], linestyle = '-', linewidth = 0.5, color = 'skyblue', label = 'Elevation (derivative)');
    parax2.plot(dictTimerw5['Trw5' + str(n)], dictZ_derivative["Z'" + str(n)], linestyle = '-', linewidth = 0.5, color = 'skyblue', label = 'Elevation (derivative)');

    # chart formatting
    ax1.set_title(f'{location} {surface} Figure No. {figure_number}\n')

    ax1.set_xlabel('Time (seconds)', fontstyle = 'italic');
    ax1.set_ylabel('Applied Pressure (psi)', fontstyle = 'italic', labelpad = 15);
    parax1.set_ylabel('Derivative', fontstyle = 'italic', labelpad = 15);
    ax1.legend(bbox_to_anchor = (0.90,-.40), ncol = 3, fontsize = 'smaller');

    ax2.set_xlabel('Time (seconds)', fontstyle = 'italic');
    ax2.set_ylabel('Elevation (m)', fontstyle = 'italic', labelpad = 20);
    parax2.set_ylabel('Derivative', fontstyle = 'italic', labelpad = 20);
    ax2.legend(bbox_to_anchor = (1,-.40), ncol = 3, fontsize = 'smaller');

    ax2.set_title('\n')

    listLoadCurrent = dictLoad['L' + str(n)];
    listZCurrent = dictZ['Z' + str(n)];

    maxLoadValue = round(max(listLoadCurrent),2);
    minLoadValue = round(min(listLoadCurrent),2);
    delLoadValue = round(maxLoadValue - minLoadValue, 2);
    delLoadValues.append(delLoadValue);

    maxZValue = round(max(listZCurrent),2);
    minZValue = round(min(listZCurrent),2);
    delZValue = round(maxZValue - minZValue, 2);
    delZValues.append(delZValue)

    ax1.annotate(f'Max. Pressure = {maxLoadValue} psi\nMin. Pressure = {minLoadValue} psi\nDelta Pressure = {delLoadValue} psi',
              xy=(0.4, -1.35), xycoords='axes fraction',
              xytext=(-20, 20), textcoords='offset pixels',
              horizontalalignment='left',
              verticalalignment='bottom',
              fontsize = 'smaller',
              bbox = dict(boxstyle = 'round', fc = '0.9'));

    ax2.annotate(f'Max. El. = {maxZValue} (m)\nMin. El. = {minZValue} (m)\nDelta El. = {delZValue} (m)',
              xy=(0.4, -1.35), xycoords='axes fraction',
              xytext=(-20, 20), textcoords='offset pixels',
              horizontalalignment='left',
              verticalalignment='bottom',
              fontsize = 'smaller',
              bbox = dict(boxstyle = 'round', fc = '0.9'));

    plt.savefig(f'{sessionName}_Clip{n}.png', bbox_inches = 'tight')

    figure_number += 1

  print(f'length of delLoadValues #{file_ticker}: {len(delLoadValues)}')
  print(f'length of delZValues #{file_ticker}: {len(delZValues)}\n')

  print(f'delLoad: {delLoadValues}')
  print(f'delZ: {delZValues}\n')

  dict_load_delta_values['lD' + str(file_ticker)] = delLoadValues

  for list_ticker in range(0, len(delLoadValues)):
    load_delta_values.append(delLoadValues[list_ticker])

  dict_Z_delta_values['zD' + str(file_ticker)] = delZValues

  for list_ticker in range(0, len(delZValues)):
    Z_delta_values.append(delZValues[list_ticker])

#find line of best fit
slope, intercept = np.polyfit(load_delta_values, Z_delta_values, 1)

#add points to plot
plt.scatter(load_delta_values, Z_delta_values)

fit_line = []

for i in range(0,len(load_delta_values)):
  fit_line.append(slope * load_delta_values[i] + intercept)

#add line of best fit to plot
plt.plot(load_delta_values, fit_line, linestyle = '-')

r_array = np.corrcoef(np.array(load_delta_values), np.array(Z_delta_values))
r_value = r_array[0,1]
print(r_value)

#find line of best fit
slope, intercept = np.polyfit(load_delta_values, Z_delta_values, 1)

#add points to plot
plt.scatter(load_delta_values, Z_delta_values, color = 'cornflowerblue', edgecolor = 'k')

fit_line = []

for i in range(0,len(load_delta_values)):
  fit_line.append(slope * load_delta_values[i] + intercept)

#add line of best fit to plot
plt.plot(load_delta_values, fit_line, linestyle = '-', color = 'midnightblue')

# print(r2_score(lS, zS))
r_array = np.corrcoef(np.array(load_delta_values), np.array(Z_delta_values))
r_value = r_array[0,1]
print(r_value)

plt.savefig(f'{location}_{surface}_DeltaValues.png', bbox_inches = 'tight')

plt.annotate(f'R = {round(r_value,3)}\nLine of Best Fit = {round(slope,3)}*x + {round(intercept,2)}',
              xy=(0.025, 0.975), xycoords='axes fraction',
              textcoords='offset pixels',
              horizontalalignment='left',
              verticalalignment='top',
              fontsize = 'smaller',
              bbox = dict(boxstyle = 'round', fc = '0.9'));

plt.xlabel('Change in Applied Pressure (psi)', fontstyle = 'italic');
plt.ylabel('Change in Elevation (m)', fontstyle = 'italic', labelpad = 15);

from statistics import mean

avg_delta_Load = mean(load_delta_values)
avg_delta_Z = mean(Z_delta_values)

print(avg_delta_Load)
print(avg_delta_Z)

!zip -r /content/file.zip /content
from google.colab import files
files.download("/content/file.zip")
