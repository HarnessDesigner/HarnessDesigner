import json

in_path = 'separated/splices.json'
out_path = 'output/splices.json'

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


'''
part_number, 
description, 
mfg=None, 
family=None, 
series=None,
color=None, 
image=None, 
datasheet=None, 
cad=None, 
min_temp=None,
max_temp=None, 
model3d=None, 

material=None, 
plating=None,  
type=None,  # NOQA
min_dia=0.0, 
max_dia=0.0,
resistance=0.0, 
length=0.0, 
weight=0.0
'''

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
    compat_housings = None
    compat_terminals = None

    material = None
    plating = None
    type = None
    min_dia = 0.0
    max_dia = 0.0
    resistance = 0.0
    length = 0.0
    weight = 0.0

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

        if label == 'Joints & Splice Product Type':
            if type:
                continue

            values = feature.get('primaryValues', [])
            if values:
                type = values[0].get('value', None)

        if label == 'Splice Type':
            if type:
                continue

            values = feature.get('primaryValues', [])
            if values:
                type = values[0].get('value', None)

        if label == 'Compatible Insulation Diameter Range':
            if min_dia or max_dia:
                continue

            values = feature.get('primaryValues', [])
            if values:
                min_dia, max_dia = get_diameter(values[0].get('value', ''))

        if label == 'Insulation Material':
            if material:
                continue

            values = feature.get('primaryValues', [])
            if values:
                material = values[0].get('value', None)

        if label == 'Contact Base Material':
            if plating:
                continue

            values = feature.get('primaryValues', [])
            if values:
                plating = values[0].get('value', None)

        if label == 'Product Length':
            if length:
                continue

            values = feature.get('primaryValues', [])
            if values:
                length = float(values[0].get('value', '0.0'))

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
        material=None,
        plating=None,
        type=None,  # NOQA
        min_dia=min_dia,
        max_dia=max_dia,
        resistance=resistance,
        length=length,
        weight=weight
    ))

    if model3d is not None:
        model3d_count += 1

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


print(len(out_data))
print(model3d_count)
