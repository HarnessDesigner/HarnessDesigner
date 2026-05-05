import os
import json

in_path = 'separated/bundles.json'
out_path = 'output/bundles.json'

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


'''
part_number, 
description, 
mfg=None, 
family=None, 
series=None,
color=None, 
material=None, 
image=None, 
datasheet=None, 
cad=None,
shrink_temp=None, 
min_temp=None, 
max_temp=None, 
protection=None,
rigidity='', 
shrink_ratio='', 
wall='', 
min_dia=0.0, 
max_dia=0.0,
adhesive_ids=None, 
weight=0.0

'''
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
    shrink_temp = None
    shrink_ratio = ''
    rigidity = ''
    wall = ''
    protection = []
    model3d = None  # *
    weight = 0.0
    min_dia = 0.0
    max_dia = 0.0
    material = None
    adhesive_ids = []

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

    shape_code = None

    for feature in features:
        label = feature.get('label', '')

        if label == 'Flexibility':
            if rigidity:
                continue

            values = feature.get('primaryValues', [])
            if values:
                rigidity = values[0].get('value', '')

        if label == 'Expanded Inside Diameter (Min)':
            if max_dia:
                continue

            values = feature.get('primaryValues', [])
            if values:
                max_dia = float(values[0].get('value', ''))

        if label == 'Recovered Inside Diameter (Max)':
            if min_dia:
                continue

            values = feature.get('primaryValues', [])
            if values:
                min_dia = float(values[0].get('value', ''))

        if label == 'Resistance Protection':
            if protection:
                continue

            values = []
            for value in feature.get('primaryValues', []):
                values.append(value['value'])

            protection = '\n'.join(values)

        if label == 'Mechanical Resistance':
            for value in feature.get('primaryValues', []):
                protection.append(value['value'])

        if label == 'Wall Type':
            if wall:
                continue

            values = feature.get('primaryValues', [])
            if values:
                wall = values[0].get('value', '')

        if label == 'Shrink Ratio':
            if shrink_ratio:
                continue

            values = feature.get('primaryValues', [])
            if values:
                shrink_ratio = values[0].get('value', '')

        if label == 'Primary Product Material':
            if material:
                continue

            values = feature.get('primaryValues', [])
            if values:
                material = values[0].get('value', '')

        if label == 'Recovery Temperature':
            if shrink_temp:
                continue

            values = feature.get('primaryValues', [])
            if values:
                shrink_temp = int(values[0].get('value', None))

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

    if family is not None and family.lower() == mfg.lower():
        family = mfg
        mfg = 'TE Connectivity'

    if color is None:
        color = 'Black'

    if model3d is not None:
        model3d_count += 1

    if protection:
        protection = '\n'.join(protection)
    else:
        protection = None

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
        min_dia=min_dia,
        max_dia=max_dia,
        wall=wall,
        adhesive_ids=adhesive_ids,
        shrink_ratio=shrink_ratio,
        shrink_temp=shrink_temp,
        min_temp=min_temp,
        max_temp=max_temp,
        model3d=model3d,
        rigidity=rigidity,
        weight=weight,
        material=material,
        protection=protection,
    ))

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))

print(len(out_data))
print(model3d_count)
