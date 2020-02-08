## 简介

一个计算EVE Online工业材料的小工具,丑,但是实用
http://lhdg.cc/

## 安装

- 安装Python3.8.1
- 安装mysql,并导入sql
- 下载代码
```
git clone https://github.com/zhlzhl123/evetool.git
```
- 安装requirements
```
pip install -r requirements.txt
```
- 设置setting.py
```
cp settings_example.py settings.py
vi settings.py
```
- 安装uwsgi
```
pip install uwsgi
uwsgi --http :8000 --module evetool.wsgi
```

## 使用

- 获取token并进入计算界面
- 设置参数,其中
```
update_price 勾选并点击保存后,使之后的计算获取Jita估价

use_remain 勾选后,使下一次就算使用库存,需要先Inventory,格式比如
Phenolic Composites 50000
Fernite Carbide 2333333

update_index 勾选并点击保存后,更新一次星系系数,如果你是第一个用户,还会更新所有物品的adjusted price
```
- 点击每一个start按钮意味着,把该按钮上方填入的数据作为输入,计算后面所需的产物。比如,在Products输入Muninn 1然后点击下方start,在Advanced Moon Materials输入Phenolic Composites 981117然后点击下方start
- 其中Products和T1框可以按照[Name Total_Num ME Runs]格式输入,如果没有设置全部参数则将自动生成,比如在Products中输入:(在末尾添加!参数,如下方Sabre,可自定义该产物的建筑材料减免)
```
Muninn 50 4 2
Falcon 50 4 2
Sabre 100 4 2 !90
Wasp II 100 4 10
damage control II 100 4 10
Rhea 1 4 1
Quake L 100 10 100
```
- 其他地方,Components_t2, Adv, Pro, Metal则可以输入[Name Total_Num],如在Adv中输入
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
- 计算配矿时,需要在Metal中依次输入金属数量,化矿率和要使用的压缩矿,比如
```
Tritanium 30250000
Pyerite 8250050
Mexallon 1925050
Isogen 506000
Nocxium 126550
Zydrine 51700
Megacyte 20900

89.3

Compressed Bright Spodumain
Compressed Crimson Arkonor
Compressed Iridescent Gneiss
Compressed Onyx Ochre
Compressed Sharp Crokite
Compressed Triclinic Bistot
```