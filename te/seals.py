# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json

in_path = 'separated/seals.json'
out_path = 'output/seals.json'

te_url = 'https://api.te.com/'

with open(in_path, 'r') as f:
    in_data = json.loads(f.read())

out_data = []


def get_temperatures(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val, max_val = val[0]
    else:
        min_val, max_val = val

    return int(min_val), int(max_val)



def get_diameter(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val = max_val = val[0]
    else:
        min_val, max_val = val

    return float(min_val), float(max_val)


model3d_count = 0

for product in in_data:
    part_number = product.get('marketingPartNumNormalized', None)
    description = product.get('friendlyDescription', '')
    mfg = product.get('brand', None)
    family = None  # *
    series = None  # *
    color = None  # *
    image = None  # *
    datasheet = None  # *
    cad = None  # *
    min_temp = None  # *
    max_temp = None  # *
    model3d = None  # *
    length = 0.0
    width = 0.0
    height = 0.0
    weight = 0.0
    type = None
    hardness = -1
    lubricant = ''
    o_dia = 0.0
    i_dia = 0.0
    wire_dia_min = 0.0
    wire_dia_max = 0.0
    compat_housings = None
    compat_terminals = None

    if part_number is None:
        part_number = product.get('tcpn', None)

    if part_number is None:
        continue

    if mfg is None:
        continue

    for doc in product.get('documents', []):
        doc_type = doc.get('type', '')

        if (
            doc_type == 'Customer View Model' and
            '3d_' in doc.get('format', '') and
            model3d is None
        ):
            model3d = doc.get('url', None)
        elif doc_type == 'Customer Drawing' and cad is None:
            cad = doc.get('url', None)

        elif doc_type == 'Specification Or Standard' and datasheet is None:
            datasheet = doc.get('url', None)

    images = product.get('images', [])

    if images:
        image = te_url + images[0].get('imageUrl', '')
    else:
        images = product.get('primaryImages', [])

        if images:
            image = te_url + images[0]['path'] + images[0]['imageName']

    features = product.get('primaryFeatures', [])

    for feature in features:
        label = feature.get('label', '')

        if label == 'Compatible Insulation Diameter Range':
            if wire_dia_min or wire_dia_max:
                continue

            values = feature.get('primaryValues', [])
            if values:
                wire_dia_min, wire_dia_max = get_diameter(values[0].get('value', ''))

        if label == 'Compatible Cable Diameter Range':
            if wire_dia_min or wire_dia_max:
                continue

            values = feature.get('primaryValues', [])
            if values:
                wire_dia_min, wire_dia_max = get_diameter(values[0].get('value', ''))

        if label == 'Connector Seal & Plug Type':
            if type:
                continue

            values = feature.get('primaryValues', [])
            if values:
                type = values[0].get('value', None)

        if label == 'Seal Type':
            if type:
                continue

            values = feature.get('primaryValues', [])
            if values:
                type = values[0].get('value', None)

        if label == 'Shore A Hardness':
            if hardness:
                continue

            values = feature.get('primaryValues', [])
            if values:
                hardness = values[0].get('value', None)

        if label == 'Contains Lubricant':
            if lubricant:
                continue

            values = feature.get('primaryValues', [])
            if values:
                lubricant = values[0].get('value', None)

        if label == 'Product Length':
            if length:
                continue

            values = feature.get('primaryValues', [])
            if values:
                length = float(values[0].get('value', '0.0'))

        if label == 'Product Width':
            if width:
                continue

            values = feature.get('primaryValues', [])
            if values:
                width = float(values[0].get('value', '0.0'))

        if label == 'Cavity Diameter':
            if o_dia:
                continue

            values = feature.get('primaryValues', [])
            if values:
                o_dia = float(values[0].get('value', '0.0'))

        if label == 'Operating Temperature Range':
            if min_temp and max_temp:
                continue

            values = feature.get('primaryValues', [])
            if values:
                min_temp, max_temp = get_temperatures(values[0].get('value', ''))

        if label == 'Primary Product Color':
            if color:
                continue

            values = feature.get('primaryValues', [])
            if values:
                color = values[0].get('value', '')

    productFamily = product.get('productFamily', None)
    if productFamily is not None:
        for crumb in productFamily.get('crumbTrailItems', []):
            if family:
                break

            family = crumb.get('name', None)

    seriesTrail = product.get('seriesTrail', None)
    if seriesTrail is not None:
        for crumb in seriesTrail.get('crumbTrailItems', []):
            if series:
                break

            series = crumb.get('name', None)

    if family is None and 'TE' not in mfg:
        family = mfg
        mfg = 'TE Connectivity'

    if family is not None and family.lower() == mfg.lower():
        family = mfg
        mfg = 'TE Connectivity'

    if color is None:
        color = 'Gray'

    out_data.append(dict(
        part_number=part_number,
        description=description,
        mfg=mfg,
        family=family,
        series=series,
        color=color,
        image=image,
        datasheet=datasheet,
        cad=cad,
        min_temp=min_temp,
        max_temp=max_temp,
        model3d=model3d,
        type=type,
        length=length,
        width=width,
        height=height,
        weight=weight,
        hardness=hardness,
        lubricant=lubricant,
        o_dia=o_dia,
        i_dia=i_dia,
        wire_dia_min=wire_dia_min,
        wire_dia_max=wire_dia_max,
        compat_housings=compat_housings,
        compat_terminals=compat_terminals,
    ))

    if model3d is not None:
        model3d_count += 1

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


print(len(out_data))
print(model3d_count)
