from django.shortcuts import render
from cal.models import User, Sdenames, Sdeconvert, Sdematerial, Sderuns , Sdecate , Sdeore
import xml.etree.ElementTree as ET
from urllib import request as urllib_request
import re
import math
import json
import requests
from scipy.optimize import linprog


def init(request):
    status_init = 1
    return render(request, "main.html", {"status_init": status_init})


def get_info(request):
    user_token = request.GET.get("token", None)
    try:
        info = User.objects.get(token=user_token)
        status = 1
    except:
        info = {}
        status = 0
    return render(request, "main.html", {"info": info, "status": status})


def save(request):
    new_info = request.POST.dict()
    del new_info["csrfmiddlewaretoken"]
    if "update_index" in new_info.keys():
        del new_info["update_index"]
        url = '''http://api.eve-industry.org/system-cost-index.xml?name=%s''' % new_info["system"]
        raw = urllib_request.urlopen(url)
        raw_xml = ET.fromstring(raw.read())
        new_info["index_manufacturing"] = float(raw_xml[0][0].text)
        new_info["index_reaction"] = float(raw_xml[0][6].text)
        raw_adjprice = urllib_request.urlopen(
            "https://esi.evetech.net/latest/markets/prices/?datasource=tranquility").read().decode()
        for i in eval(raw_adjprice):
            Sdenames.objects.filter(typeid=i["type_id"]).update(adjprice=i["adjusted_price"])
    if "update_price" in new_info.keys():
        new_info["update_price"] = 1
    else:
        new_info["update_price"] = 0
    User.objects.filter(token=new_info["token"]).update(**new_info)
    return render(request, "main.html", {"info": new_info, "status": 1})


def start(request, mode):
    # 分割为[[first req],[second req],......]
    base_quantity_final = {}
    req = request.POST.dict()
    info = User.objects.get(token=req["token"])
    if mode == 1:
        req_list = req["req"].split("\r\n")
        req_list = [i for i in req_list if i != '']
        list = []
        name = ""
        n = 0
        m = 0
        for i in req_list:
            list.append([])
            for j in re.split(' |,|\t', i):
                try:
                    int(j)
                    if m == 0:
                        list[n].append(name.strip(" "))
                        name = ""
                        m += 1
                    list[n].append(j)
                except:
                    name += j + " "
            n += 1
            m = 0
        material_list = {}
        print(list)
        # 计算组件数量
        for item in list:
            [name, me, run, total, *me_structure] = item
            id = Sdenames.objects.get(typename=name).typeid
            if me_structure:
                me_structure = me_structure[0]
                pass
            elif Sdenames.objects.get(typeid=id).groupid in [1527, 831, 1283, 893, 830, 324, 1305, 541, 1534]:
                me_structure = info.me_ship_s
            elif Sdenames.objects.get(typeid=id).groupid in [543, 380, 1202, 906, 832, 894, 358, 1972, 963, 540]:
                me_structure = info.me_ship_m
            else:
                me_structure = 100
            me = float(me)
            run = int(run)
            total = int(total)
            me_structure = float(me_structure)
            [full_runs, single_runs] = divmod(total, run)
            id_b = Sdeconvert.objects.get(producttypeid=id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * run, 2)),
                    run) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in material_list.keys():
                    material_list[material_typeid] += material_quantity
                    base_quantity_final[material_typeid] += line.quantity * total
                else:
                    material_list[material_typeid] = material_quantity
                    base_quantity_final[material_typeid] = line.quantity * total
    # 分开T1和T2部分并计算Advanced产物
    material_list_1 = {}
    material_list_name_1 = {}
    material_list_2 = {}
    material_list_name_2 = {}
    material_list_adv = {}
    material_list_adv_name = {}
    base_quantity_component = {}
    if mode == 2:
        req = request.POST.dict()
        req["req"] = ""
        info = User.objects.get(token=req["token"])
        req_list = req["component_t2"].split("\r\n")
        name = ""
        for i in req_list:
            temp = i.split(" ")
            for j in temp:
                try:
                    quantity = int(j)
                except:
                    name += j + " "
            if name != " ":
                try:
                    comp_id = Sdenames.objects.filter(typename=name.strip(" ")).filter(groupid=334).get().typeid
                except:
                    comp_id = Sdenames.objects.filter(typename=name.strip(" ")).filter(groupid=913).get().typeid
                material_list_name_2[name.strip(" ")] = quantity
                material_list_2[comp_id] = quantity
            name = ""
    if mode == 1:
        material_list_pro = {}
        material_list_pro_name = {}
        for id, quantity in material_list.items():
            if Sdenames.objects.get(typeid=id).groupid in [334, 913]:
                material_list_2[id] = quantity
                material_list_name_2[Sdenames.objects.get(typeid=id).typename] = quantity
                # 计算Advanced产物
                id_b = Sdeconvert.objects.get(producttypeid=id).typeid
                material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
                run = int(Sderuns.objects.get(typeid=id_b).maxproductionlimit)
                [full_runs, single_runs] = divmod(quantity, run)
                for line in material_table:
                    material_typeid = line.materialtypeid
                    material_quantity = max(
                        math.ceil(round(int(line.quantity) * 0.9 * info.me_component / 100 * run, 2)), run) * full_runs
                    material_quantity += max(
                        math.ceil(round(int(line.quantity) * 0.9 * info.me_component / 100 * single_runs, 2)),
                        single_runs)
                    if material_typeid in material_list_adv.keys():
                        material_list_adv[material_typeid] += material_quantity
                        material_list_adv_name[
                            Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                        base_quantity_component[material_typeid] += line.quantity * quantity
                    else:
                        material_list_adv[material_typeid] = material_quantity
                        material_list_adv_name[
                            Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                        base_quantity_component[material_typeid] = line.quantity * quantity
            elif Sdenames.objects.get(typeid=id).groupid==429:
                material_list_adv[id] = quantity
                material_list_adv_name[Sdenames.objects.get(typeid=id).typename] = quantity
            elif Sdenames.objects.get(typeid=id).groupid==428:
                material_list_pro[id] = quantity
                material_list_pro_name[Sdenames.objects.get(typeid=id).typename] = quantity
            else:
                material_list_1[id] = quantity
                material_list_name_1[Sdenames.objects.get(typeid=id).typename] = quantity
    if mode == 2:
        for id, quantity in material_list_2.items():
            id_b = Sdeconvert.objects.get(producttypeid=id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            run = int(Sderuns.objects.get(typeid=id_b).maxproductionlimit)
            [full_runs, single_runs] = divmod(quantity, run)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(math.ceil(round(int(line.quantity) * 0.9 * info.me_component / 100 * run, 2)),
                                        run) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * 0.9 * info.me_component / 100 * single_runs, 2)), single_runs)
                if material_typeid in material_list_adv.keys():
                    material_list_adv[material_typeid] += material_quantity
                    material_list_adv_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                    base_quantity_component[material_typeid] += line.quantity * quantity
                else:
                    material_list_adv[material_typeid] = material_quantity
                    material_list_adv_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                    base_quantity_component[material_typeid] = line.quantity * quantity
    # 计算复杂反应
    try:
        material_list_pro
        material_list_pro_name
    except:
        material_list_pro = {}
        material_list_pro_name = {}
    processed_fuel = {}
    processed_fuel_name = {}
    base_quantity_complex = {}
    if mode == 3:
        req = request.POST.dict()
        req["req"] = ""
        info = User.objects.get(token=req["token"])
        req_list = req["advanced"].split("\r\n")
        name_adv = ""
        for i in req_list:
            temp = i.split(" ")
            for j in temp:
                try:
                    quantity = int(j)
                except:
                    name_adv += j + " "
            if name_adv != " ":
                pro_id = Sdenames.objects.filter(typename=name_adv.strip(" ")).filter(groupid=429).get().typeid
                material_list_adv_name[name_adv.strip(" ")] = quantity
                material_list_adv[pro_id] = quantity
            name_adv = ""
    for id, quantity in material_list_adv.items():
        id_b = Sdeconvert.objects.get(producttypeid=id).typeid
        product_num = Sdeconvert.objects.get(producttypeid=id).quantity
        material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=11)
        if info.min_reaction == 0:
            run = 100
        else:
            run = int(info.min_reaction)
        [need, excessed] = divmod(quantity, product_num)
        if excessed != 0:
            need += 1
        [full_runs, single_runs] = divmod(need, run)
        for line in material_table:
            material_typeid = line.materialtypeid
            material_quantity = max(math.ceil(round(int(line.quantity) * info.me_reaction / 100 * run, 2)),
                                    run) * full_runs
            material_quantity += max(math.ceil(round(int(line.quantity) * info.me_reaction / 100 * single_runs, 2)),
                                     single_runs)
            if material_typeid in material_list_pro.keys() and Sdenames.objects.get(
                    typeid=material_typeid).groupid != 1136:
                material_list_pro[material_typeid] += material_quantity
                material_list_pro_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                base_quantity_complex[material_typeid] += line.quantity * need
            elif Sdenames.objects.get(typeid=material_typeid).groupid != 1136:
                material_list_pro[material_typeid] = material_quantity
                material_list_pro_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                base_quantity_complex[material_typeid] = line.quantity * need
            elif material_typeid in processed_fuel.keys():
                processed_fuel[material_typeid] += material_quantity
                processed_fuel_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                base_quantity_complex[material_typeid] += line.quantity * need
            else:
                processed_fuel[material_typeid] = material_quantity
                processed_fuel_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                base_quantity_complex[material_typeid] = line.quantity * need

    # 计算简单反应
    material_list_raw = {}
    material_list_raw_name = {}
    raw_fuel = {}
    raw_fuel_name = {}
    base_quantity_simple = {}
    if mode == 4:
        req = request.POST.dict()
        req["req"] = ""
        info = User.objects.get(token=req["token"])
        req_list = req["processed"].split("\r\n")
        name_adv = ""
        for i in req_list:
            temp = i.split(" ")
            for j in temp:
                try:
                    quantity = int(j)
                except:
                    name_adv += j + " "
            if name_adv != " ":
                try:
                    pro_id = Sdenames.objects.filter(typename=name_adv.strip(" ")).filter(groupid=428).get().typeid
                    material_list_pro_name[name_adv.strip(" ")] = quantity
                    material_list_pro[pro_id] = quantity
                except:
                    pass
            name_adv = ""
    for id, quantity in material_list_pro.items():
        id_b = Sdeconvert.objects.get(producttypeid=id).typeid
        product_num = Sdeconvert.objects.get(producttypeid=id).quantity
        material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=11)
        if info.min_reaction == 0:
            run = 100
        else:
            run = int(info.min_reaction)
        [need, excessed] = divmod(quantity, product_num)
        if excessed != 0:
            need += 1
        [full_runs, single_runs] = divmod(need, run)
        for line in material_table:
            material_typeid = line.materialtypeid
            material_quantity = max(math.ceil(round(int(line.quantity) * info.me_reaction / 100 * run, 2)),
                                    run) * full_runs
            material_quantity += max(math.ceil(round(int(line.quantity) * info.me_reaction / 100 * single_runs, 2)),
                                     single_runs)
            if material_typeid in material_list_raw.keys() and Sdenames.objects.get(
                    typeid=material_typeid).groupid != 1136:
                material_list_raw[material_typeid] += material_quantity
                material_list_raw_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                base_quantity_simple[material_typeid] += line.quantity * need
            elif Sdenames.objects.get(typeid=material_typeid).groupid != 1136:
                material_list_raw[material_typeid] = material_quantity
                material_list_raw_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                base_quantity_simple[material_typeid] = line.quantity * need
            elif material_typeid in raw_fuel.keys():
                raw_fuel[material_typeid] += material_quantity
                raw_fuel_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                base_quantity_simple[material_typeid] += line.quantity * need
            else:
                raw_fuel[material_typeid] = material_quantity
                raw_fuel_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                base_quantity_simple[material_typeid] = line.quantity * need

    # 合并两次反应燃料块
    total_fuel_name = {}
    for i in ["Helium Fuel Block", "Hydrogen Fuel Block", "Nitrogen Fuel Block", "Oxygen Fuel Block"]:
        try:
            total_fuel_name[i] = raw_fuel_name[i]
        except:
            pass
        try:
            total_fuel_name[i] += processed_fuel_name[i]
        except:
            pass
    # 估价
    price_status = 0
    prices = {}
    if info.update_price == 1:
        url = "https://evepraisal.com/appraisal.json"
        headers = {
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"}

        if mode == 1:
            raw_textarea = ""
            for i in list:
                raw_textarea += i[0] + " " + i[3] + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["req_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["req_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)
            raw_textarea = ""
            for name, quantity in material_list_name_1.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["component_t1_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["component_t1_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)

        if mode == 1 or mode == 2:
            raw_textarea = ""
            for name, quantity in material_list_name_2.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["component_t2_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["component_t2_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)

        if mode == 1 or mode == 2 or mode == 3:
            raw_textarea = ""
            for name, quantity in material_list_adv_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["advanced_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["advanced_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)
        if mode in [1,2,3,4]:
            raw_textarea = ""
            for name, quantity in material_list_pro_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            for name, quantity in processed_fuel_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["processed_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["processed_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)
        if mode in [1,2,3,4]:
            raw_textarea = ""
            for name, quantity in material_list_raw_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            for name, quantity in total_fuel_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices["raw_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices["raw_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)
            price_status = 1

    # 计算费用
    fee = {}
    fee_single = 0
    for id, quantity in base_quantity_final.items():
        fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
    fee["final"] = round(fee_single * info.index_manufacturing * (1 + info.tax_ship / 100) / 1000000, 2)
    fee_single = 0

    for id, quantity in base_quantity_component.items():
        fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
    fee["component"] = round(fee_single * info.index_manufacturing * (1 + info.tax_component / 100) / 1000000, 2)
    fee_single = 0

    for id, quantity in base_quantity_complex.items():
        fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
    fee["complex"] = round(fee_single * info.index_reaction * (1 + info.tax_reaction / 100) / 1000000, 2)
    fee_single = 0

    for id, quantity in base_quantity_simple.items():
        fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
    fee["simple"] = round(fee_single * info.index_reaction * (1 + info.tax_reaction / 100) / 1000000, 2)

    fee["total"] = fee["final"] + fee["component"] + fee["complex"] + fee["simple"]
    fee_status = 1

    # 筛选T1
    t1_name = {}
    t1_list = []
    t1_name_t = {}
    t1_list_t =[]
    ratio = 50
    if mode ==1:
        for id, quantity in material_list_1.items():
            if Sdecate.objects.get(groupid=Sdenames.objects.get(typeid=id).groupid).categoryid in [6, 18,22,7,87] or Sdenames.objects.get(typeid=id).groupid==873:
                t1_list.append([Sdenames.objects.get(typeid=id).typename,quantity,0,999])
    fee_status_t1=0
    metal_name={}
    fee_1={}
    price_status_1=0
    prices_t1={}
    orename=[]
    orestatus=0
    ore_result={}
    ore_total_price=0
    if mode ==5:
        fee_status = 0
        req = request.POST.dict()
        req["req"] = ""
        info = User.objects.get(token=req["token"])
        req_list = req["t1_name"].split("\r\n")
        req_list = [i for i in req_list if i != '']
        n = 0
        m = 0
        name = ""
        for i in req_list:
            t1_list.append([])
            for j in re.split(' |,|\t', i):
                try:
                    int(j)
                    if m == 0:
                        t1_list[n].append(name.strip(" "))
                        t1_name[name.strip(" ")]=j
                        name = ""
                        m += 1
                    t1_list[n].append(j)
                except:
                    name += j + " "
            try:
                t1_list[n][2]
            except:
                t1_list[n].append(0)
            try:
                t1_list[n][3]
                if Sdenames.objects.filter(adjprice__gt=1).get(typename=t1_list[n][0]).groupid==873:
                    t1_list[n][3]=40
            except:
                if Sdenames.objects.filter(adjprice__gt=1).get(typename=t1_list[n][0]).groupid==873:
                    t1_list[n].append(40)
                else:
                    t1_list[n].append(999)
            n += 1
            m = 0

        #计算旗舰组件
        t1_name_t = {}
        t1_list_t = []
        base_quantity_t1_1={}
        base_quantity_t1_2={}
        m = 0
        for item in t1_list:
            [name, total, me, run, *me_structure] = item
            me = float(me)
            run = int(run)
            total = int(total)
            id = Sdenames.objects.filter(adjprice__gt=1).get(typename__exact=name).typeid
            if Sdenames.objects.get(typeid=id).groupid in [547,883,485,1538,513,659,30]:
                t1_list[m][3]=1
                run = 1
                if me_structure:
                    me_structure = me_structure[0]
                else:
                    me_structure = info.me_cap
                me_structure = float(me_structure)
                [full_runs, single_runs] = divmod(total, run)
                id_b = Sdeconvert.objects.get(producttypeid=id).typeid
                material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
                for line in material_table:
                    material_typeid = line.materialtypeid
                    material_typename = Sdenames.objects.get(typeid=material_typeid).typename
                    material_quantity = max(
                        math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * run, 2)),
                        run) * full_runs
                    material_quantity += max(
                        math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                        single_runs)
                    if material_typename in t1_name_t.keys():
                        t1_name_t[material_typename] += material_quantity
                        n=0
                        for i in t1_list_t:
                            if i[0]==material_typename:
                                t1_list_t[n][1] +=material_quantity
                                t1_list_t[n][3] =40
                            n += 1
                        base_quantity_t1_1[material_typeid] += line.quantity * total


                    else:
                        t1_name_t[material_typename] = int(material_quantity)
                        t1_list_t.append([material_typename,int(material_quantity),10,40])
                        base_quantity_t1_1[material_typeid] = line.quantity * total

            else:
                t1_name_t[name]=total
                t1_list_t.append(item.copy())
                t1_list_t[-1][1]=int(t1_list_t[-1][1])
                base_quantity_t1_1[id] = total
            m += 1
        print(t1_list_t)

        #计算金属需求
        metal={}
        metal_name={}
        for item in t1_list_t:
            [name, total, me, run, *me_structure] = item
            id = Sdenames.objects.filter(adjprice__gt=1).get(typename__exact=name).typeid
            if me_structure:
                me_structure = me_structure[0]
            elif Sdenames.objects.get(typeid=id).groupid == 873:
                me_structure = info.me_cap_comp
            else:
                me_structure = 100
            me = float(me)
            run = int(run)
            total = int(total)
            me_structure = float(me_structure)
            [full_runs, single_runs] = divmod(total, run)
            id_b = Sdeconvert.objects.get(producttypeid=id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * run, 2)),
                    run) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in metal.keys():
                    metal[material_typeid] += material_quantity
                    metal_name[Sdenames.objects.get(typeid=material_typeid).typename] += material_quantity
                    base_quantity_t1_2[material_typeid] += line.quantity * total
                else:
                    metal[material_typeid] = material_quantity
                    metal_name[Sdenames.objects.get(typeid=material_typeid).typename] = material_quantity
                    base_quantity_t1_2[material_typeid] = line.quantity * total
        #计算T1费用
        # 计算费用
        fee_1 = {}
        fee_single = 0
        for id, quantity in base_quantity_t1_1.items():
            fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
        fee_1["final"] = round(fee_single * info.index_manufacturing * (1 + info.tax_t1 / 100) / 1000000, 2)
        fee_single = 0

        for id, quantity in base_quantity_t1_2.items():
            fee_single += Sdenames.objects.get(typeid=id).adjprice * quantity
        fee_1["component"] = round(fee_single * info.index_manufacturing * (1 + info.tax_t1 / 100) / 1000000, 2)

        fee_1["total"] = fee_1["final"] + fee_1["component"]
        fee_status_t1 = 1

        # 估价
        prices_t1 = {}
        if info.update_price == 1:
            url = "https://evepraisal.com/appraisal.json"
            headers = {
                'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"}
            raw_textarea = ""
            for i in t1_list:
                raw_textarea += i[0] + " " + str(i[1]) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices_t1["t1_final_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices_t1["t1_final_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)

            raw_textarea = ""
            for i in t1_list_t:
                raw_textarea += i[0] + " " + str(i[1]) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices_t1["t1_t_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices_t1["t1_t_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)

            raw_textarea = ""
            for name, quantity in metal_name.items():
                raw_textarea += name + " " + str(quantity) + "\r\n"
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            prices_t1["metal_buy"] = round(result_dict['appraisal']['totals']['buy'] / 1000000)
            prices_t1["metal_sell"] = round(result_dict['appraisal']['totals']['sell'] / 1000000)

            price_status_1 = 1

        #计算耗矿
        orename = req["orename"].split("\r\n")
        try:
            ratio = float(req["ratio"])
        except:
            ratio = 50
        print(ratio)
        orename = [i for i in orename if i != '']
        ore_matrix = [[],[],[],[],[],[],[]]
        b = []
        if len(orename)!=0:
            orestatus =1
            url = "https://evepraisal.com/appraisal.json"
            headers = {
                'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"}
            raw_textarea = ""
            x_bounds=[]
            for i in orename:
                raw_textarea += i + "\r\n"
                id = Sdenames.objects.get(typename__exact=i).typeid
                for j in [34,35,36,37,38,39,40]:
                    try:
                        quantity = Sdeore.objects.filter(typeid=id).get(materialtypeid=j).quantity
                    except:
                        quantity = 0
                    ore_matrix[j-34].append(-quantity*ratio/100)
                x_bounds.append((0,None))
            for j in [34, 35, 36, 37, 38, 39, 40]:
                b.append(-metal[j])
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            print(result_dict)
            price_ore=[]
            ore_temp={}
            for i in result_dict["appraisal"]["items"]:
                ore_temp[i["name"]] = i["prices"]["buy"]["max"]
            for i in orename:
                price_ore.append(ore_temp[i])
            print(price_ore)
            print(ore_matrix)
            print(b)
            res = linprog(c=price_ore, A_ub=ore_matrix, b_ub=b, bounds=x_bounds ,method="interior-point")
            print(res)
            raw_result = res.x
            ore_result={}
            n=0
            for i in orename:
                ore_result[i] = math.ceil(raw_result[n])
                n += 1
            ore_total_price = 0
            for i in range(len(orename)):
                ore_total_price += round(raw_result[i]*price_ore[i]/1000000,2)

    if mode ==6:
        req = request.POST.dict()
        req["req"] = ""
        info = User.objects.get(token=req["token"])
        orename = req["orename"].split("\r\n")
        print(orename)
        try:
            ratio = float(req["ratio"])
        except:
            ratio = 50
        print(ratio)
        orename = [i for i in orename if i != '']
        ore_matrix = [[],[],[],[],[],[],[]]
        b = []
        if len(orename)!=0:
            orestatus =1
            url = "https://evepraisal.com/appraisal.json"
            headers = {
                'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"}
            raw_textarea = ""
            x_bounds=[]
            for i in orename:
                raw_textarea += i + "\r\n"
                id = Sdenames.objects.get(typename__exact=i).typeid
                for j in [34,35,36,37,38,39,40]:
                    try:
                        quantity = Sdeore.objects.filter(typeid=id).get(materialtypeid=j).quantity
                    except:
                        quantity = 0
                    ore_matrix[j-34].append(-quantity*ratio/100)
                x_bounds.append((0,None))
            req_metal = req["metal_123"].split("\r\n")
            req_metal = [i for i in req_metal if i != '']
            metal = {}
            metal_name={}
            print(req_metal,"123")
            for i in req_metal:
                temp = i.split(" ")
                print(i)
                metal[Sdenames.objects.get(typename__exact=temp[0]).typeid]=int(temp[1])
                metal_name[temp[0]]=int(temp[1])
            for j in [34, 35, 36, 37, 38, 39, 40]:
                b.append(-metal[j])
            post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
            result = requests.post(url, headers=headers, data=post_data)
            result_dict = json.loads(result.text)
            print(result_dict)
            price_ore=[]
            ore_temp={}
            for i in result_dict["appraisal"]["items"]:
                ore_temp[i["name"]] = i["prices"]["buy"]["max"]
            for i in orename:
                price_ore.append(ore_temp[i])
            print(price_ore)
            print(ore_matrix)
            print(b)
            res = linprog(c=price_ore, A_ub=ore_matrix, b_ub=b, bounds=x_bounds ,method="interior-point")
            print(res)
            raw_result = res.x
            ore_result={}
            n=0
            for i in orename:
                ore_result[i] = math.ceil(raw_result[n])
                n += 1
            ore_total_price = 0
            for i in range(len(orename)):
                ore_total_price += round(raw_result[i]*price_ore[i]/1000000,2)

    return render(request, "main.html", {
        "info": info,
        "status": 1,
        "price_status": price_status,
        "fee_status": fee_status,
        "req": req["req"],
        "component_t1": material_list_name_1,
        "component_t2": material_list_name_2,
        "advanced": material_list_adv_name,
        "processed": material_list_pro_name,
        "processed_fuel": processed_fuel_name,
        "raw": material_list_raw_name,
        "raw_fuel": total_fuel_name,
        "prices": prices,
        "fee": fee,
        "t1_list":t1_list,
        "t1_comp":t1_name_t,
        "metal":metal_name,
        "fee_status_t1":fee_status_t1,
        "fee_1":fee_1,
        "prices_t1":prices_t1,
        "price_status_1":price_status_1,
        "orename":orename,
        "orestatus":orestatus,
        "ore":ore_result,
        "ore_total_price":ore_total_price,
        "ratio":ratio,
    })
