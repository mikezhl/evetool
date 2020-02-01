from django.shortcuts import render
from cal.models import User, Sdenames, Sdeconvert, Sdematerial, Sderuns, Sdecate, Sdeore, Inventory
import xml.etree.ElementTree as ET
from urllib import request as urllib_request
import re
import math
import json
import requests
from scipy.optimize import linprog


# Init
def init(request):
    return render(request, "main.html", {"status_init": 1})

# Switch
def cal_init(request):
    user_token = request.GET.get("token")
    try:
        info = User.objects.get(token=user_token)
        return render(request, "cal.html", {"info": info, "status": 1})
    except:
        return render(request, "main.html", {"info": {}, "status": 0})

# Turn the input raw data into dictionary {typeid : [total,me,runs,name]
def process_l(raw):
    output = {}
    lines = raw.split("\r\n")
    lines_full = [i for i in lines if i != '']
    m = 0
    customised = 0
    for i in lines_full:
        name = ""
        line = re.split(' |,|\t| ', i)
        print(line)
        for j in line:
            print(j)
            if j.startswith("!"):
                print(j)
                customised = float(j[1:])
                break
            if m ==3:
                break
            try:
                k = int(j)
                m += 1
            except:
                name += j + " "
            if m ==1:
                name = name.strip(" ")
                item_id = Sdenames.objects.filter(adjprice__gt=1).get(typename__exact=name).typeid
                output[item_id] = []
            if m > 0:
                output[item_id].append(k)
        if m < 3:
            if Sdenames.objects.get(typeid=item_id).groupid in [334, 913]:
                runs = int(Sderuns.objects.get(typeid=item_id).maxproductionlimit)
            else:
                runs = 10000
        if m == 0:
            output[item_id].append(1)
            output[item_id].append(0)
            output[item_id].append(runs)
            output[item_id].append(name)
        elif m == 1:
            output[item_id].append(0)
            output[item_id].append(runs)
            output[item_id].append(name)
        elif m ==2:
            output[item_id].append(runs)
            output[item_id].append(name)
        elif m ==3:
            output[item_id].append(name)
        m = 0
        if customised != 0:
            output[item_id].append(customised)
            customised = 0;
    return output

# Turn the input raw data into dictionary {typeid : [total,name]
def process_s(raw):
    output = {}
    lines = raw.split("\r\n")
    lines_full = [i for i in lines if i != '']
    m = 0
    for i in lines_full:
        name = ""
        line = re.split(' |,|\t| ', i)
        for j in line:
            try:
                k = int(j)
                if m == 0:
                    name = name.strip(" ")
                    item_id = Sdenames.objects.filter(adjprice__gt=1).get(typename__exact=name).typeid
                    output[item_id] = []
                    m = 1
                output[item_id].append(k)
            except:
                name += j + " "
        m = 0
        output[item_id].append(name)
    return output

# Main Cal function
def main(request, mode):
    # All variables returned
    Data = {}
    user_token = request.POST.get("token")
    status = 1
    use_remain = 0
    price = {}
    fee = {}

    # Get Data from request:
    if mode != 11:
        status = 1
        if "use_remain" in request.POST.dict():
            use_remain = 1
        else:
            use_remain = 0
        Data["info"] = User.objects.get(token=user_token)
        # Numbers
        for i in ["ore_ratio"]:
            try:
                Data[i] = float(request.POST.get(i))
            except:
                Data[i] = 50
        # Long Dictionary
        for i in ["products", "components_t1", "components_t2", "t1_input", "t1_pro"]:
            try:
                Data[i] = process_l(request.POST.get(i))
            except:
                Data[i] = {}
        # Short Dictionary
        for i in ["inventory", "adv", "pro", "raw", "metal", "ore_result", "pro_fuel", "raw_fuel"]:
            try:
                Data[i] = process_s(request.POST.get(i))
            except:
                Data[i] = {}
        # List
        try:
            Data["ore"] = [i for i in request.POST.get("ore").split("\r\n") if i != '']
        except:
            Data["ore"] = {}
    # Get user info
    if mode == 11:
        try:
            Data["info"] = User.objects.get(token=user_token)
        except:
            status = 0
        for i in ["inventory", "products", "components_t1", "components_t2", "adv", "pro", "raw", "t1_input", "ore", "t1_pro", "metal", "ore_result", "pro_fuel", "raw_fuel"]:
            Data[i] = {}
        Data["ore_ratio"] = 50
    # Save user info
    if mode == 12:
        new_info = {}
        new_info["token"] = user_token
        if "update_price" in request.POST.dict():
            new_info["update_price"] = 1
        else:
            new_info["update_price"] = 0
        for i in ["system", "tax_reaction", "tax_component", "tax_standard", "tax_cap", "tax_super", "index_reaction",
                  "index_manufacturing", "me_reaction", "me_component", "me_ship_m", "me_ship_s", "me_others",
                  "me_cap_comp", "me_cap", "min_reaction"]:
            new_info[i] = request.POST.get(i)
        if "update_index" in request.POST.dict():
            url = '''http://api.eve-industry.org/system-cost-index.xml?name=%s''' % new_info["system"]
            raw = urllib_request.urlopen(url)
            raw_xml = ET.fromstring(raw.read())
            new_info["index_manufacturing"] = float(raw_xml[0][0].text)
            new_info["index_reaction"] = float(raw_xml[0][6].text)
            raw_adjprice = urllib_request.urlopen(
                "https://esi.evetech.net/latest/markets/prices/?datasource=tranquility").read().decode()
            for i in eval(raw_adjprice):
                Sdenames.objects.filter(typeid=i["type_id"]).update(adjprice=i["adjusted_price"])
        Data["info"] = new_info
        User.objects.filter(token=user_token).update(**new_info)
    # From Product
    if mode == 1:
        pass



    return render(request, "cal.html", {
        "status": status,
        "use_remain": use_remain,
        "info": Data["info"],
        "inventory": Data["inventory"],

        "products": Data["products"],
        "components_t1": Data["components_t1"],
        "components_t2": Data["components_t2"],
        "adv": Data["adv"],
        "pro": Data["pro"],
        "raw": Data["raw"],
        "pro_fuel": Data["pro_fuel"],
        "raw_fuel": Data["raw_fuel"],

        "t1_input": Data["t1_input"],
        "ore_ratio": Data["ore_ratio"],
        "ore": Data["ore"],
        "ore_result": Data["ore_result"],
        "t1_pro": Data["t1_pro"],
        "metal": Data["metal"],

        "price": price,
        "fee": fee,

    })
