import requests


POST_URL = 'https://aptivcatalog.searchapi-na.hawksearch.com/api/v2/search/'

SEARCH_REQUEST_DATA = {
    "ClientData": {
        "UserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:147.0) Gecko/20100101 Firefox/147.0",
        "VisitId": "d6af1751-06f7-43ed-9a9c-fe4727fbce72",
        "VisitorId": "c1a10a57-d6df-41c7-b620-26d9e27dc11c",
        "Custom": {"custom": None}
    },
    "Keyword": "",
    "FacetSelections": {},
    "PageNo": 1,
    # this is the number we increment to get the next page of items
    "IndexName": "",
    "IgnoreSpellcheck": False,
    "IsInPreview": True,
    "ClientGuid": "425f6702e15a49298831856bdfdfc6ea",
    "Is100CoverageTurnedOn": False,
    "Query": "itemrelation_en: \"child\" AND productseriesproductline_en: \"Connectors\"",
    "CustomUrl": "/connectors"
}

DETAIL_REQUEST_DATA = {
    "ClientData": {
        "UserAgent": None,
        "VisitId": None,
        "VisitorId": None,
        "Custom": {}
    },
    "Keyword": "33284004",  # part number
    "FacetSelections": {},
    "IndexName": None,
    "IsInPreview": True,
    "ClientGuid": "425f6702e15a49298831856bdfdfc6ea",
    "Is100CoverageTurnedOn": True
}


def get_page(page_num):
    SEARCH_REQUEST_DATA['PageNo'] = page_num
    response = requests.post(POST_URL, data=SEARCH_REQUEST_DATA)
    contents = response.json()

    return contents['Pagination']['NofPages'], contents['Results']


def get_item_detail(part_number):
    DETAIL_REQUEST_DATA['Keyword'] = part_number
    response = requests.post(POST_URL, data=DETAIL_REQUEST_DATA)
    contents = response.json()
    try:
        return contents['Results'][0]['Document']
    except IndexError:
        return None

import os
import json

seals = {}
terminals = {}
covers = {}
housings = {}
tpa_locks = {}
cpa_locks = {}
some_other_locks = {}
accessories = {}
boots = {}

used_part_numbers = []


def read_part(data):
    try:
        part_type = data['itemcomponenttype_en'][0]
    except KeyError:
        try:
            part_type = data['itemdrmproductfamily_en'][0]
        except KeyError:
            print(json.dumps(data, indent=4))
            raise

        if part_type.upper()[:-1] in ('CONNECTOR', 'COVER', 'SEAL',
                                      'TERMINAL', 'LOCKING DEVICE'):

            part_type = part_type.upper()[:-1]

    part_number = data['itempartnumberapn_en'][0]
    description = data['itempimitemdescription_en'][0]

    if 'LOCK COV CONN' in description.upper():
        part_type = 'COVER'

    if (
        'LOCK COV SPACER' in description.upper() or
        'COV STRAIN RLF' in description.upper() or
        'LOCK RETAINER' in description.upper() or
        'MOUN LEVER' in description.upper() or
        'ASST LEVER' in description.upper() or
        'LOCK STRAIN RLF FERRULE' in description.upper()
    ):
        part_type = 'ACCESSORY'

    elif (
        'LOCK SECONDARY COMB' in description.upper() or
        'LOCK SECONDARY SLC' in description.upper() or
        'LOCK STRAIN RLF' in description.upper() or
        'LOCK SECONDARY' in description.upper() or
        'LOCK PLR' in description.upper() or
        'LOCK TERM' in description.upper() or
        'PRIMARY LOCK' in description.upper() or
        ' TPA' in description.upper() or
        'TPA ' in description.upper()
    ):
        part_type = 'TPA LOCKING DEVICE'
    elif (
        'LOCK CONN' in description.upper() or
        'CONNECTOR POSITION ASSURANCE' in description.upper() or
        ' CPA' in description.upper() or
        'CPA ' in description.upper()
    ):
        part_type = 'CPA LOCKING DEVICE'

    if part_type == 'Accessories':
        if 'DRESS COVER' in description.upper():
            part_type = 'COVER'

        elif 'SEAL' in description.upper():
            part_type = 'SEAL'

        elif 'BOOT' in description.upper():
            part_type = 'BOOT'

        else:
            part_type = 'ACCESSORY'

    elif part_type == 'MepaPinheader':
        part_type = 'CONNECTOR'
    elif part_type == 'MOUNTING DEVICE':
        part_type = 'TPA LOCKING DEVICE'
    elif part_type == 'HVInterconnects':
        part_type = 'CONNECTOR'
    elif part_type == 'NCBSeals':
        part_type = 'SEAL'
    elif part_type == 'FERRULE':
        part_type = 'ACCESSORY'
    elif part_type == 'CIRCUIT PROTECTION':
        part_type = 'ACCESSORY'
    elif part_type == 'GROMMET':
        part_type = 'BOOT'

    manufacturer = 'Aptiv'

    if part_number in used_part_numbers:
        return

    used_part_numbers.append(part_number)
    print(part_type, part_number, description)

    image = data.get('itemresourceimages_en', [None])[0]
    datasheet = data.get('productresourcedatasheets_en', [None])[0]
    cad = data.get('itemresourcedrawings_en', [None])[0]
    model3d = data.get('itemresource3ddrawings_en', [None])[0]
    min_temp = data.get('producttempmin_en', [None])[0]  # "-40°C"
    max_temp = data.get('producttempmax_en', [None])[0]  # "+150°C"
    length = float(data.get('itemlength_en', [0.0])[0])
    width = float(data.get('itemwidth_en', [0.0])[0])
    height = float(data.get('itemheight_en', [0.0])[0])
    weight = float(data.get('itemhsgnetweight_en', [0.0])[0])
    family = data.get('productmarketingname_en', [None])[0]
    series = data.get('productmarketingnameext_en', [None])[0]
    color = data.get('itemcolour_en', ['Transparent'])[0].title()

    if part_type == "CONNECTOR":
        gender = data.get('itemhsggender_en', [None])[0]
        direction = data.get('itemhsgwiredirectioncableexitorientation_en', [None])[0]
        cavity_lock = data.get('itemhsgprimarylocktype_en', [''])[0].lower()
        sealing = True if data.get('itemhsgsealing_en', ['False'])[0] == 'True' else False
        num_pins = int(data.get('itemhsgcavities_en', [0])[0])
        terminal_sizes = [float(item) for item in data.get('itembladesizes_en', [])]

        if len(terminal_sizes) == 3:
            terminal_size_counts = [
                int(data.get('itemhsgbladesize1qty_en', [0])[0]),
                int(data.get('itemhsgbladesize2qty_en', [0])[0]),
                int(data.get('itemhsgbladesize3qty_en', [0])[0])]
        elif len(terminal_sizes) == 2:
            terminal_size_counts = [
                int(data.get('itemhsgbladesize1qty_en', [0])[0]),
                int(data.get('itemhsgbladesize2qty_en', [0])[0])]
        else:
            terminal_size_counts = [
                int(data.get('itemhsgbladesize1qty_en', [0])[0])]

        compat_terminals = [item.strip() for item in
                            data.get('itemitemrelatedterminals_en', [''])[0].split(', ')
                            if item.strip()]

        compat_seals = [item.strip() for item in
                        data.get('itemitemrelatedseals_en', [''])[0].split(', ')
                        if item.strip()]

        compat_housings = [item.strip() for item in
                           data.get('itemitemmatesto_en', [''])[0].split(', ')
                           if item.strip()]

        ip_rating = data.get('productsealingrating_en', [None])[0]

        for pn in compat_housings:
            p_data = get_item_detail(pn)
            if p_data is None:
                print('ERROR: COMPAT_HOUSING', pn)
                continue

            read_part(p_data)

        for pn in compat_seals:
            p_data = get_item_detail(pn)
            if p_data is None:
                print('ERROR: SEAL', pn)
                continue

            read_part(p_data)

        for pn in compat_terminals:
            p_data = get_item_detail(pn)
            if p_data is None:
                print('ERROR: TERMINAL', pn)
                continue

            read_part(p_data)

        compat_cpas = []
        compat_tpas = []
        compat_covers = []

        acc = [item.strip() for item in
               data.get('itemitemaccessories_en', [''])[0].split(', ')
               if item.strip()]

        for pn in acc[:]:
            p_data = get_item_detail(pn)
            if p_data is None:
                print('ERROR: ACCESSORY', pn)
                continue

            p_type = read_part(p_data)
            if p_type == 'COVER':
                compat_covers.append(pn)
                acc.remove(pn)

            elif p_type == 'TPA LOCKING DEVICE':
                compat_tpas.append(pn)
                acc.remove(pn)

            elif p_type == 'CPA LOCKING DEVICE':
                compat_cpas.append(pn)
                acc.remove(pn)

        if part_number not in housings:
            housings[part_number] = dict(
                part_number=part_number,
                description=description,
                manufacturer=manufacturer,
                family=family,
                series=series,
                color=color,
                gender=gender,
                direction=direction,
                image=image,
                datasheet=datasheet,
                cad=cad,
                min_temp=min_temp,
                max_temp=max_temp,
                cavity_lock=cavity_lock,
                sealing=sealing,
                num_pins=num_pins,
                terminal_sizes=terminal_sizes,
                terminal_size_counts=terminal_size_counts,
                compat_cpas=compat_cpas,
                compat_tpas=compat_tpas,
                compat_covers=compat_covers,
                compat_terminals=compat_terminals,
                compat_seals=compat_seals,
                compat_housings=compat_housings,
                ip_rating=ip_rating,
                length=length,
                width=width,
                height=height,
                weight=weight,
                model3d=model3d
            )

    elif part_type == 'SEAL':
        lubricant = data.get('itemsealoilcontent_en', [''])[0].title()
        seal_sub_type = data.get('itemsealsubtype_en', [''])[0].title()
        seal_type = data.get('itemsealtype_en', [''])[0].title()
        o_dia = float(data.get('itemsealoutsidediameter_en', [0.0])[0])
        shape = data.get('itemsealsealshape_en', [''])[0].title()
        color = data.get('itemsealcolour_en', [''])[0].title()
        cavity_size = float(data.get('itemsealcavitysize_en', [0.0])[0])
        hardness = int(data.get('itemsealhardness_en', [0])[0])

        i_dia = 0.0
        wire_dia_min = 0.0
        wire_dia_max = 0.0
        if part_number not in seals:
            seals[part_number] = dict(
                part_number=part_number,
                description=description,
                manufacturer=manufacturer,
                series=series,
                color=color,
                image=image,
                datasheet=datasheet,
                cad=cad,
                min_temp=min_temp,
                max_temp=max_temp,
                type=seal_type,
                hardness=hardness,
                lubricant=lubricant,
                length=length,
                o_dia=o_dia,
                i_dia=i_dia,
                wire_dia_min=wire_dia_min,
                wire_dia_max=wire_dia_max,
                weight=weight,
                model3d=model3d
            )

    elif part_type == 'TERMINAL':
        blade_size = float(data.get('itemtermbladesize_en', [0.0])[0])

        wire_dia_min = float(data.get('itemtermcablediametermin_en', [0.0])[0])
        wire_dia_max = float(data.get('itemtermcablediametermax_en', [0.0])[0])

        min_wire_cross = float(
            data.get('itemtermmincablecrosssection_en', [0.0])[0]
            )
        max_wire_cross = float(
            data.get('itemtermmaxcablecrosssection_en', [0.0])[0]
            )

        plating = data.get('itemtermplating_en', [''])[0].title()
        gender = data.get('itemtermgender_en', [''])[0].title()
        cavity_lock = data.get('itemtermlockingmechanism_en', [''])[0].title()
        sealing = data.get('itemtermsealing_en', [''])[0].title() == 'Yes'
        if part_number not in terminals:
            terminals[part_number] = dict(
                part_number=part_number,
                description=description,
                manufacturer=manufacturer,
                family=family,
                series=series,
                plating=plating,
                image=image,
                datasheet=datasheet,
                cad=cad,
                gender=gender,
                sealing=sealing,
                cavity_lock=cavity_lock,
                blade_size=blade_size,
                wire_dia_min=wire_dia_min,
                wire_dia_max=wire_dia_max,
                min_wire_cross=min_wire_cross,
                max_wire_cross=max_wire_cross,
                length=length,
                width=width,
                height=height,
                weight=weight,
                model3d=model3d
            )

    elif part_type == 'COVER':
        if part_number not in covers:
            covers[part_number] = dict(
                part_number=part_number,
                description=description,
                manufacturer=manufacturer,
                family=family,
                series=series,
                color=color,
                image=image,
                datasheet=datasheet,
                cad=cad,
                min_temp=min_temp,
                max_temp=max_temp,
                length=length,
                width=width,
                height=height,
                weight=weight,
                model3d=model3d
            )

    else:
        lock_type = data.get('itemgsdfamily_en', [''])[0].title()
        other_data = dict(
            part_number=part_number,
            description=description,
            manufacturer=manufacturer,
            family=family,
            series=series,
            color=color,
            image=image,
            datasheet=datasheet,
            cad=cad,
            min_temp=min_temp,
            max_temp=max_temp,
            length=length,
            width=width,
            height=height,
            weight=weight,
            model3d=model3d,
            lock_type=lock_type
        )

        if part_type == 'TPA LOCKING DEVICE':
            if part_number not in tpa_locks:
                tpa_locks[part_number] = other_data
        elif part_type == 'CPA LOCKING DEVICE':
            if part_number not in cpa_locks:
                cpa_locks[part_number] = other_data
        elif 'BOOT' in part_type:
            if part_number not in boots:
                boots[part_number] = other_data
        elif part_type == 'LOCKING DEVICE':
            if part_number not in some_other_locks:
                some_other_locks[part_number] = other_data
        else:
            if part_number not in accessories:
                accessories[part_number] = other_data

    return part_type


page_count = 1
total_pages = 99999999

base_path = os.path.dirname(__file__)

save_path = os.path.join(base_path, '..', 'database', 'setup_db', 'data', 'aptiv')

if not os.path.exists(save_path):
    os.mkdir(save_path)

while page_count <= total_pages:
    print('PAGE:', page_count, f'({total_pages})')
    total_pages, results = get_page(page_count)
    page_count += 1

    for item in results:
        read_part(item['Document'])

with open(os.path.join(save_path, 'seals.json'), 'w') as f:
    f.write(json.dumps(seals, indent=2))

with open(os.path.join(save_path, 'terminals.json'), 'w') as f:
    f.write(json.dumps(terminals, indent=2))

with open(os.path.join(save_path, 'covers.json'), 'w') as f:
    f.write(json.dumps(covers, indent=2))

with open(os.path.join(save_path, 'housings.json'), 'w') as f:
    f.write(json.dumps(housings, indent=2))

with open(os.path.join(save_path, 'tpa_locks.json'), 'w') as f:
    f.write(json.dumps(tpa_locks, indent=2))

with open(os.path.join(save_path, 'cpa_locks.json'), 'w') as f:
    f.write(json.dumps(cpa_locks, indent=2))

with open(os.path.join(save_path, 'some_other_locks.json'), 'w') as f:
    f.write(json.dumps(some_other_locks, indent=2))

with open(os.path.join(save_path, 'accessories.json'), 'w') as f:
    f.write(json.dumps(accessories, indent=2))

with open(os.path.join(save_path, 'boots.json'), 'w') as f:
    f.write(json.dumps(accessories, indent=2))
