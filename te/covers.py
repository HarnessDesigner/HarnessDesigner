# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json

in_path = 'separated/covers.json'
out_path = 'output/covers.json'

te_url = 'https://api.te.com/'

with open(in_path, 'r') as f:
    in_data = json.loads(f.read())

out_data = []

covers = []
boots = []
housings = []
transitions = []


def get_temperatures(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val, max_val = val[0]
    else:
        min_val, max_val = val

    return int(min_val), int(max_val)


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
    pins = 0
    compat_housings = None
    direction = None

    if product.get('baseCategory', '') == 'Wire Protection & Management':
        transitions.append(product)
        continue

    features = product.get('primaryFeatures', [])
    is_housing = False

    for feature in features:
        label = feature['label']
        if label == 'Hood & Base Connector Product Type':
            values = feature.get('primaryValues', [])
            if (
                values and
                values[0]['value'] in (
                    'Base Housing', 'Hood & Base Housing Assembly With Inserts')
            ):
                housings.append(product)
                is_housing = True
                break

    if is_housing:
        continue

    if 'Base Housing' in description:
        raise RuntimeError(part_number)

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

        if label == 'Number of Positions':
            if pins:
                continue

            values = feature.get('primaryValues', [])
            if values:
                pins = int(values[0].get('value', ''))

        if label == 'Cable Entry Location':
            if direction:
                continue

            values = feature.get('primaryValues', [])
            if values:
                direction = values[0].get('value', None)

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

    for fg in product.get('featureGroups', []):
        label = fg['label']
        if label == 'Dimensions':
            for feature in fg.get('features', []):
                label2 = feature['label']

                values = feature.get('primaryValues', [])
                if values:
                    if label2 == 'Product Height':
                        if not height:
                            height = float(values[0]['value'])

                    elif label2 == 'Product Length':
                        if not length:
                            length = float(values[0]['value'])

                    elif label2 == 'Product Width':
                        if not width:
                            width = float(values[0]['value'])
    covers.append(product)

    if direction is None:
        direction = 'Straight'

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
        length=length,
        width=width,
        height=height,
        weight=weight,
        pins=pins,
        direction=direction,
        compat_housings=compat_housings,
    ))

with open('separated/new_covers.json', 'w') as f:
    f.write(json.dumps(covers, indent=4))

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


with open('separated/addl_housings.json', 'w') as f:
    f.write(json.dumps(housings, indent=4))


with open('separated/addl_transitions.json', 'w') as f:
    f.write(json.dumps(transitions, indent=4))

print(len(housings))
print(len(transitions))
print(len(out_data))
