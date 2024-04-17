# RTKGNSS_SaltmarshPlatform_CUAHSIHydro
CUAHSI Hydroinformatics Fellowship: Quantification of Saltmarsh Platform for RTK-GNSS Integration into Ecosystem Modeling

Overall project results are used to evaluate the relationship between applied pressure and recorded elevation in the context of RTK-GNSS surveying on soft surfaces. 

Specifically, data processed using this code is intended to aid in creating a numerical definition of saltmarsh platform, which will assist coastal researchers in resolving the ambiguity of saltmarsh elevation quantification. Our hope is that users will use this to a) create control data (i.e., data taken on hard surfaces with little topographic ambiguity) and to b) produce compelling data on the saltmarsh itself.

## Hardware

This fellowship involved the synthesis of traditional RTK-GNSS topographic survey equipment (SOKKIA GRX3 GNSS receiver + Carlson RT5 with SurvPC data collector) with a conceptual setup of applied-pressure metering devices (Omega LC103B-25 load cell + Omega IN-USBH signal conditioner) mounted on the traditional RTK range pole. The final setup looked a bit like this:

![image](https://github.com/harbinm/RTKGNSS_SaltmarshPlatform_CUAHSIHydro/assets/166173659/2d7e84bb-61b2-431d-8b38-56a596460315)

Links to those products can be found below:
  - SOKKIA GRX3: https://us.sokkia.com/sokkia-care-products/grx3-gnss-receiver
  - Carlson RT5: https://carlsonsw.com/product/carlson-rt5-rtk5
  - Omega LC103B-25: https://www.omega.com/en-us/force-and-strain-measurement/load-cells/lc103b/p/LC103B-25
  - Omega IN-USBH: https://www.omega.com/en-us/data-acquisition/signal-conditioners/specialty-conditioners/in-usbh-sig-cond/p/IN-USBH

## How to Use

### *Input files:* 
  - Elevation data in the form of a .rw5.csv file; using a Carlson SurvPC enabled data collector, convert the .rw5 project file into a .csv file at the following link:
      http://www.carlsonemea.com/cwa/report/index.php?lang=RO
  - Applied Pressure data in the form of a .xlsx file exported by the Omega Digital Transducer Application
    
### *Input data ONLY on the following lines:*
  - Line 18: ```rw5_files = ['...rw5.csv'] #List of files containing elevation data converted from raw (.rw5) format to comma-separated values (.csv) format```
  - Line 19: ```INUSBH_files = ['...xlsx'] #List of files containing applied pressure data```
  - Line 25: ```area_toposhoe = ... #Floating point number representative of topo-shoe surface area; used to convert load data to pressure```

### *Output files:*
This code will automatically generate saved .png images and will create a .zip file of all output; if you do not want this, be sure to comment out all lines containing ```plt.savefig()``` as well as the last 3 lines.
  - Time series of complete survey
  - Time series of all identified survey points (this might be A LOT depending on the size of your survey)
  - Scatter plot relating change in pressure vs. change in elevation over a given point
  - .zip file of all plots

    
