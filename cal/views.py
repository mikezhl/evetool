from django.shortcuts import render
from cal.models import User, Sdenames, Sdeconvert, Sdematerial, Sderuns, Sdecate, Sdeore
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
    lines_full =[]
    for i in lines:
        if re.search('[a-z]',i):
            lines_full.append(i)
    m = 0
    customised = 0
    for i in lines_full:
        name = ""
        line = re.split(' |,|\t| ', i)
        for j in line:
            if j.startswith("!"):
                customised = float(j[1:])
                break
            if m ==3:
                break
            try:
                k = int(j)
                m += 1
            except:
                name += j + " "
            if m ==1 or len(line) == 1:
                name = name.strip(" ")
                name = name.strip(" ")
                item_id = Sdenames.objects.filter(adjprice__gt=1).get(typename__exact=name).typeid
                output[item_id] = []
            if m > 0:
                output[item_id].append(k)
        if m != 0 and m < 3:
            if Sdenames.objects.get(typeid=item_id).groupid in [334, 913]:
                id_b = int(Sdeconvert.objects.get(producttypeid=item_id).typeid)
                runs = int(Sderuns.objects.get(typeid=id_b).maxproductionlimit)
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
    lines_full = []
    for i in lines:
        if re.search('[a-z]', i):
            lines_full.append(i)
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
    fee_temp = {}

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
            Data[i] = process_l(request.POST.get(i))
        # Short Dictionary
        for i in ["inventory", "adv", "pro", "raw", "metal", "ore_result"]:
            Data[i] = process_s(request.POST.get(i))
        # Hidden
        for i in ["pro_fuel","raw_fuel"]:
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
                  "me_cap_comp", "me_cap", "me_super", "min_reaction"]:
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
        temp = {}
        for i in ["components_t1", "components_t2"]:
            Data[i] = {}
        fee_temp["products"] = {}
        for item_id, [total, me, runs, name, *me_structure_p] in Data["products"].items():
            if me_structure_p:
                me_structure = me_structure_p[0]
            elif Sdenames.objects.get(typeid=item_id).groupid in [1527, 831, 1283, 893, 830, 324, 1305, 541, 1534]:
                me_structure = Data["info"].me_ship_s
            elif Sdenames.objects.get(typeid=item_id).groupid in [543, 380, 1202, 906, 832, 894, 358, 1972, 963, 540, 833]:
                me_structure = Data["info"].me_ship_m
            else:
                me_structure = 99
            me_structure = float(me_structure)
            total = int(total)
            me = float(me)
            runs = int(runs)
            [full_runs, single_runs] = divmod(total, runs)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * runs, 2)),
                    runs) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in temp.keys():
                    temp[material_typeid] += material_quantity
                    fee_temp["products"][material_typeid] += line.quantity * total
                else:
                    temp[material_typeid] = material_quantity
                    fee_temp["products"][material_typeid] = line.quantity * total
            # 分类产物
            for item_id, total in temp.items():
                name = Sdenames.objects.get(typeid=item_id).typename
                if use_remain ==1:
                    try:
                        total = max(total - Data["inventory"][item_id][0],0)
                    except:
                        pass
                if Sdenames.objects.get(typeid=item_id).groupid in [334, 913]:
                    id_b = int(Sdeconvert.objects.get(producttypeid=item_id).typeid)
                    Data["components_t2"][item_id] = [total, 10, int(Sderuns.objects.get(typeid=id_b).maxproductionlimit),name]
                elif Sdenames.objects.get(typeid=item_id).groupid == 429:
                    Data["adv"][item_id] = [total, name]
                elif Sdenames.objects.get(typeid=item_id).groupid == 428:
                    Data["pro"][item_id] = [total, name]
                elif Sdenames.objects.get(typeid=item_id).groupid == 428:
                    Data["pro"][item_id] = [total, name]
                else:
                    Data["components_t1"][item_id] = [total, 0, 10000, name]
                check_others = Sdecate.objects.get(groupid=Sdenames.objects.get(typeid=item_id).groupid).categoryid in [6, 18,22,7,87]
                check_capcomp = Sdenames.objects.get(typeid=item_id).groupid==873
                if check_others or check_capcomp:
                    if check_capcomp:
                        me = 10
                        run = 40
                    else:
                        me = 0
                        run = 1
                    Data["t1_input"][item_id] = [total, me, run, name]
    # From Components
    if mode in [1, 2]:
        if mode ==2:
            for i in ["products", "components_t1"]:
                Data[i] = {}
        for i in ["adv"]:
            Data[i] = {}
        fee_temp["components_t2"] = {}
        for item_id, [total, me, runs, name, *me_structure_c] in Data["components_t2"].items():
            if me_structure_c:
                me_structure = me_structure_c[0]
            else:
                me_structure = Data["info"].me_component
            me_structure = float(me_structure)
            total = int(total)
            me = float(me)
            runs = int(runs)
            [full_runs, single_runs] = divmod(total, runs)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * runs, 2)),
                    runs) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in Data["adv"].keys():
                    Data["adv"][material_typeid][0] += material_quantity
                    fee_temp["components_t2"][material_typeid] += line.quantity * total
                else:
                    Data["adv"][material_typeid] = [material_quantity, Sdenames.objects.get(typeid=material_typeid).typename]
                    fee_temp["components_t2"][material_typeid] = line.quantity * total
        if use_remain == 1:
            for item_id, [total, name] in Data["adv"].items():
                try:
                    Data["adv"][item_id][0] = max(total - Data["inventory"][item_id][0], 0)
                except:
                    pass
    # From Adv
    if mode in [1, 2, 3]:
        if mode ==3:
            for i in ["products", "components_t1","components_t2"]:
                Data[i] = {}
        for i in ["pro"]:
            Data[i] = {}
        fee_temp["adv"] = {}
        for item_id, [total, name, *me_structure_r] in Data["adv"].items():
            product_num = Sdeconvert.objects.get(producttypeid=item_id).quantity
            if me_structure_r:
                me_structure = me_structure_r[0]
            else:
                me_structure = Data["info"].me_reaction
            me_structure = float(me_structure)
            total = int(total)
            [need, excessed] = divmod(total, product_num)
            if excessed != 0:
                need += 1
            [full_runs, single_runs] = divmod(need, Data["info"].min_reaction)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=11)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * me_structure / 100 * Data["info"].min_reaction, 2)),
                    Data["info"].min_reaction) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in Data["pro"].keys():
                    Data["pro"][material_typeid][0] += material_quantity
                    fee_temp["adv"][material_typeid] += line.quantity * total
                else:
                    Data["pro"][material_typeid] = [material_quantity, Sdenames.objects.get(typeid=material_typeid).typename]
                    fee_temp["adv"][material_typeid] = line.quantity * total
        temp = {}
        for item_id, [total,name] in Data["pro"].items():
            if use_remain ==1:
                try:
                    if Sdenames.objects.get(typeid=item_id).groupid!=1136:
                        total = max(total - Data["inventory"][item_id][0],0)
                except:
                    pass
            if Sdenames.objects.get(typeid=item_id).groupid==1136:
                Data["pro_fuel"][item_id] = [total, name]
            else:
                temp[item_id] = [total, name]
        Data["pro"] = temp
    # From Pro
    if mode in [1, 2, 3, 4]:
        if mode ==4:
            for i in ["products", "components_t1","components_t2", "adv", "pro_fuel"]:
                Data[i] = {}
        for i in ["raw"]:
            Data[i] = {}
        fee_temp["pro"] = {}
        delete_list = []
        for item_id, [total, name, *me_structure_r] in Data["pro"].items():
            if Sdenames.objects.get(typeid=item_id).groupid!=428:
                delete_list.append(item_id)
                Data["pro_fuel"][item_id] = [total,name]
                continue
            product_num = Sdeconvert.objects.get(producttypeid=item_id).quantity
            if me_structure_r:
                me_structure = me_structure_r[0]
            else:
                me_structure = Data["info"].me_reaction
            me_structure = float(me_structure)
            total = int(total)
            [need, excessed] = divmod(total, product_num)
            if excessed != 0:
                need += 1
            [full_runs, single_runs] = divmod(need, Data["info"].min_reaction)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=11)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * me_structure / 100 * Data["info"].min_reaction, 2)),
                    Data["info"].min_reaction) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in Data["raw"].keys():
                    Data["raw"][material_typeid][0] += material_quantity
                    fee_temp["pro"][material_typeid] += line.quantity * total
                else:
                    Data["raw"][material_typeid] = [material_quantity, Sdenames.objects.get(typeid=material_typeid).typename]
                    fee_temp["pro"][material_typeid] = line.quantity * total
        temp = {}
        if delete_list:
            for i in delete_list:
                del Data["pro"][i]
        for item_id, [total,name] in Data["raw"].items():
            if use_remain ==1:
                try:
                    total = max(total - Data["inventory"][item_id][0],0)
                except:
                    pass
            if Sdenames.objects.get(typeid=item_id).groupid==1136:
                try:
                    last_time = Data["pro_fuel"][item_id][0]
                except:
                    last_time = 0
                Data["raw_fuel"][item_id] = [total + last_time, name]
            else:
                temp[item_id] = [total, name]
        Data["raw"] = temp
    # From T1 Input
    if mode ==5:
        fee_temp["t1_input"] = {}
        fee_temp["t1_pro"] = {}
        for i in ["t1_pro", "metal", "ore_result"]:
            Data[i] = {}
        for item_id, [total, me, runs, name, *me_structure_t1] in Data["t1_input"].items():
            gp_id = Sdenames.objects.get(typeid=item_id).groupid
            if gp_id not in [547, 883, 485, 1538, 513, 659, 30]:
                Data["t1_pro"][item_id] = Data["t1_input"][item_id]
                continue
            if me_structure_t1:
                me_structure = me_structure_t1[0]
            elif gp_id in [659, 30]:
                me_structure = Data["info"].me_super
            else:
                me_structure = Data["info"].me_cap
            me_structure = float(me_structure)
            total = int(total)
            me = float(me)
            runs = int(runs)
            [full_runs, single_runs] = divmod(total, runs)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * runs, 2)),
                    runs) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in Data["t1_pro"].keys():
                    Data["t1_pro"][material_typeid][0] += material_quantity
                    fee_temp["t1_input"][material_typeid] += line.quantity * total
                else:
                    Data["t1_pro"][material_typeid] = [material_quantity, 10, 40, Sdenames.objects.get(typeid=material_typeid).typename]
                    fee_temp["t1_input"][material_typeid] = line.quantity * total
        if use_remain == 1:
            for item_id, [total, me, runs, name] in Data["t1_pro"].items():
                try:
                    Data["t1_pro"][item_id][0] = max(total - Data["inventory"][item_id][0], 0)
                except:
                    pass
        for item_id, [total, me, runs, name, *me_structure_t1] in Data["t1_pro"].items():
            gp_id = Sdenames.objects.get(typeid=item_id).groupid
            if me_structure_t1:
                me_structure = me_structure_t1[0]
            elif gp_id == 873:
                me_structure = Data["info"].me_cap_comp
            else:
                me_structure = Data["info"].me_others
            me_structure = float(me_structure)
            total = int(total)
            me = float(me)
            runs = int(runs)
            [full_runs, single_runs] = divmod(total, runs)
            id_b = Sdeconvert.objects.get(producttypeid=item_id).typeid
            material_table = Sdematerial.objects.filter(typeid=id_b).filter(activityid=1)
            for line in material_table:
                material_typeid = line.materialtypeid
                material_quantity = max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * runs, 2)),
                    runs) * full_runs
                material_quantity += max(
                    math.ceil(round(int(line.quantity) * (100 - me) / 100 * me_structure / 100 * single_runs, 2)),
                    single_runs)
                if material_typeid in Data["metal"].keys():
                    Data["metal"][material_typeid][0] += material_quantity
                    fee_temp["t1_pro"][material_typeid] += line.quantity * total
                else:
                    Data["metal"][material_typeid] = [material_quantity, Sdenames.objects.get(typeid=material_typeid).typename]
                    fee_temp["t1_pro"][material_typeid] = line.quantity * total
            if use_remain == 1:
                for item_id, [total, name] in Data["metal"].items():
                    try:
                        Data["metal"][item_id][0] = max(total - Data["inventory"][item_id][0], 0)
                    except:
                        pass
    # Cal Compressed Ore
    if mode ==6:
        Data["ore_result"] = {}
        ore_matrix = [[], [], [], [], [], [], []]
        b = []
        url = "https://evepraisal.com/appraisal.json"
        headers = {
            'user-agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36"}
        raw_textarea = ""
        x_bounds = []
        for i in Data["ore"]:
            raw_textarea += i + "\r\n"
            id = Sdenames.objects.get(typename__exact=i).typeid
            for j in [34, 35, 36, 37, 38, 39, 40]:
                try:
                    quantity = Sdeore.objects.filter(typeid=id).get(materialtypeid=j).quantity
                except:
                    quantity = 0
                ore_matrix[j - 34].append(-quantity * Data["ore_ratio"] / 100)
            x_bounds.append((0, None))
        for j in [34, 35, 36, 37, 38, 39, 40]:
            b.append(-Data["metal"][j][0])
        post_data = {'market': "jita", "raw_textarea": raw_textarea.encode()}
        result = requests.post(url, headers=headers, data=post_data)
        result_dict = json.loads(result.text)
        print(result_dict)
        price_ore = []
        ore_temp = {}
        for i in result_dict["appraisal"]["items"]:
            ore_temp[i["name"]] = i["prices"]["buy"]["max"]
        for i in Data["ore"]:
            price_ore.append(ore_temp[i])
        print(price_ore)
        print(ore_matrix)
        print(b)
        res = linprog(c=price_ore, A_ub=ore_matrix, b_ub=b, bounds=x_bounds, method="interior-point")
        print(res)
        raw_result = res.x
        n = 0
        for i in Data["ore"]:
            Data["ore_result"][i] = [math.ceil(raw_result[n]),i]
            n += 1

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
