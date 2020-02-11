## Introduction

A simple tool for EVE Online industry.
http://lhdg.cc/

## Dependencies

- Python3.8.1
- Mysql，import /sql/evetool.sql

## Install
Download
```
git clone https://github.com/zhlzhl123/evetool.git
```
Install requirements
```
pip install -r requirements.txt
```
Config setting.py
```
cp settings_example.py settings.py
vi settings.py
```
Install uwsgi
```
pip install uwsgi
uwsgi --http :8000 --module evetool.wsgi
```

## Instructions

Click "new user" and "ok", each token will save a set of settings.

Set those coefficients that affect the calculation

- update_price: if it is checked and then click save, later calculations will find the latest prices at jita
- use_inventory: if it is checked, the next calculation will include what is remain in the inventory.
- update_index if it is checked and then click save, all the indexes of system will be updated. If your user_id is 1, adjusted prices for the calculation of job fee will be updated as well (take a long time)
- others are straightforward.

You can calculate the materials needed from any steps. A correct format of inputs is needed. Each line should contain only one item, with coefficients follow by it in order specify below. 
Features:
- Only name is required, if others coefficients are missing, it will use default value. If Structure_ME is not given, it will use the coresponding value from the settings automatically
- The products you want must be enter into corresponding blocks, like put "Muninn" in "T2 Products" or put "Rupture" in "T1"
- A "Total Estimated" value is given when you calculating from "T2 Products" or "T1", it is a sum of the raw materials buy price and the total job fees needed.
Formats of inputs:
- For T2 Products and T1: Name Total_Number=1 ME=0 Runs_per_Time=10000 !Structure_ME=0
- For others: Name Total_Number=1
- Example for calculating "T2 Products":
```
Muninn 50 4 2
Falcon,50
Sabre 100 4 2 !90
Wasp II 100 4 10
damage control II 100 4 10
Rhea
Quake L 100 10 100
```
- Example for calculating "Advanced Moon Materials"
```
Phenolic Composites 331102
Fernite Carbide 11993397
Ferrogel 24679
Sylramic Fibers 2621911
Hypersynaptic Fibers 13125
Nanotransistors 143347
Plasmonic Metamaterials 155116
Fermionic Condensates 3582
Fullerides 262502
```
Calculation for the compressed ore will give a combination has minimum price. It need these (An example):
- Amount of metal needed
```
Tritanium 30250000
Pyerite 8250050
Mexallon 1925050
Isogen 506000
Nocxium 126550
Zydrine 51700
Megacyte 20900
```
- Reprocess ratio
```
89.3
```
- Type of compressed ore you have
```
Compressed Bright Spodumain
Compressed Crimson Arkonor
Compressed Iridescent Gneiss
Compressed Onyx Ochre
Compressed Sharp Crokite
Compressed Triclinic Bistot
```
- Example
![image](https://github.com/zhlzhl123/evetool/blob/master/example/example.jpg)
