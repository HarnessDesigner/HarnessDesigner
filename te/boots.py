
import os
import json
#
# file_num = 1
#
# filename = f'products{file_num}.json'
#
# boots = []
#
# while os.path.exists(filename):
#     print(filename)
#     with open(filename, 'r') as f:
#         data = json.loads(f.read())
#
#     file_num += 1
#     filename = f'products{file_num}.json'
#
#     for product in data:
#         if product.get('parentCategory', '') in (
#             'Insulation Boots & Sleeves',
#             "EMI Shielded Boots",
#             "Heat Shrink Boots",
#             "Connector Strain Relief",
#
#         ):
#             boots.append(product)
#
#
# with open('separated/boots.json', 'w') as f:
#     f.write(json.dumps(boots, indent=4))


in_path = 'separated/boots.json'
out_path = 'output/boots.json'

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
direction=None, 
image=None, 
datasheet=None,
cad=None, 
min_temp=None, 
max_temp=None, 
model3d=None, 
length=0.0,
width=0.0, 
height=0.0, 
weight=0.0, 
compat_housings=None

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
    model3d = None  # *
    length = 0.0
    width = 0.0
    height = 0.0
    weight = 0.0
    min_dia = 0.0
    max_dia = 0.0
    material = None
    protection = None
    compat_housings = None

    if 'Ferrule' in description:
        continue

    if 'Pull Loop' in description:
        continue

    if 'Bushing' in description:
        continue

    if 'Lock Ring' in description:
        continue

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

        if label == 'Molded Part Shape Code':
            if shape_code:
                continue

            values = feature.get('primaryValues', [])
            if values:
                shape_code = values[0].get('value', '')

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

        if label == 'Material Systems Code':
            if material:
                continue

            values = feature.get('primaryValues', [])
            if values:
                material = 'Material Systems Code ' + values[0].get('value', '')

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

    if shape_code:
        series = shape_code

    if color is None:
        color = 'Black'

    if model3d is not None:
        model3d_count += 1

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
        min_temp=min_temp,
        max_temp=max_temp,
        model3d=model3d,
        length=length,
        width=width,
        height=height,
        weight=weight,
        material=material,
        protection=protection,
        compat_housings=compat_housings,
    ))

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))

print(len(out_data))
print(model3d_count)
