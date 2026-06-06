# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

import json
from decimal import Decimal
import math

in_path = 'separated/housings.json'
out_path = 'output/housings.json'
model3d_count = 0
te_url = 'https://api.te.com/'
out_data = []


with open(in_path, 'r') as f:
    in_data = json.loads(f.read())


with open('separated/addl_housings.json', 'r') as f:
    in_data.extend(json.loads(f.read()))


def get_temperatures(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val, max_val = val[0]
    else:
        min_val, max_val = val

    return int(min_val), int(max_val)


def _d(v):
    return Decimal(str(v))


def awg_to_mm2(awg: int) -> float:
    d_in = _d(0.005) * (_d(92) ** ((_d(36) - _d(awg)) / _d(39)))
    d_mm = d_in * _d(25.4)
    area_mm2 = (_d(math.pi) / _d(4)) * (d_mm ** _d(2))
    return float(round(area_mm2, 4))


def get_terminal_size(val):

    if 'Size' in val:
        val = int(val.replace('Size', '').strip())
        return awg_to_mm2(val)

    if 'K' in val:
        return None

    output = ''
    for char in val:
        if char in '123456789.0':
            output += char

    if output.startswith('.'):
        output = '0' + output

    return float(_d(output))


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
    direction = None  # *
    gender = None  # *
    cavity_lock = None  # *
    ip_rating = 'IP00'  # *
    seal_type = None
    cpa_lock_type = None  # *
    sealing = 0  # *
    rows = 0  # *
    shape = None  # *
    num_pins = 0  # *
    terminal_sizes = []  # *
    terminal_size_counts = []
    centerline = 0.0  # *
    compat_cpas = None
    compat_tpas = None
    compat_covers = None
    compat_terminals = None
    compat_seals = None
    compat_housings = None
    compat_boots = None
    length = 0.0  # *
    width = 0.0  # *
    height = 0.0  # *
    weight = 0.0  # *
    cover_point3d = None
    seal_point3d = None
    boot_point3d = None
    tpa_lock_1_point3d = None
    tpa_lock_2_point3d = None
    cpa_lock_point3d = None

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

    skip = False

    for feature in features:
        label = feature.get('label', '')

        if label == 'Number of Positions':
            if num_pins:
                continue

            values = feature.get('primaryValues', [])
            if values:
                num_pins = int(values[0].get('value', '0'))

        if label == 'Number of Coaxial Contacts':
            if num_pins:
                continue

            values = feature.get('primaryValues', [])
            if values:
                num_pins = int(values[0].get('value', '0'))

        if label == 'Number of Rows':
            if rows:
                continue

            values = feature.get('primaryValues', [])
            if values:
                rows = int(values[0].get('value', '0'))

        if label == 'Sealable':

            values = feature.get('primaryValues', [])
            if values:
                sealing = int(values[0].get('value', '') == 'Yes')

        # if label == 'Contact Current Rating (Max)':
        #     if current:
        #         continue
        #
        #     values = feature.get('primaryValues', [])
        #     if values:
        #         current = float(values[0].get('value', ''))

        if label == 'Operating Temperature Range':
            if min_temp and max_temp:
                continue

            values = feature.get('primaryValues', [])
            if values:
                min_temp, max_temp = get_temperatures(values[0].get('value', ''))

        if label == 'Connector Product Type':
            values = feature.get('primaryValues', [])
            if values:
                p_type = values[0].get('value', '')
                if p_type not in (
                    'Housing',
                    'Connector Assembly',
                    'Housing Kit',
                    'Connector Kit',
                    'Housing Assembly'
                ):
                    skip = True

        if label == 'Centerline (Pitch)':
            if centerline:
                continue

            values = feature.get('primaryValues', [])
            if values:
                centerline = float(values[0].get('value', '0.0'))

        if label == 'Circular Connector Type':
            if gender:
                continue

            values = feature.get('primaryValues', [])
            if values:
                value = values[0].get('value', '')
                if value == 'Circular Connector Receptacle':
                    gender = 'Female'
                elif value == 'Circular Connector Plug':
                    gender = 'Male'
                else:
                    raise RuntimeError

        if label == 'Data Bus Connector Type':
            if gender:
                continue

            values = feature.get('primaryValues', [])
            if values:
                value = values[0].get('value', '')
                if value == 'Jack':
                    gender = 'Female'
                elif value == 'Plug':
                    gender = 'Male'
                else:
                    raise RuntimeError

        if label == 'RF Connector Style':
            if gender:
                continue

            values = feature.get('primaryValues', [])
            if values:
                value = values[0].get('value', '')
                if value == 'Jack':
                    gender = 'Female'
                elif value == 'Plug':
                    gender = 'Male'
                else:
                    raise RuntimeError

        if label == 'Docking Connector Style':
            if gender:
                continue

            values = feature.get('primaryValues', [])
            if values:
                value = values[0].get('value', '')
                if value == 'Receptacle':
                    gender = 'Female'
                elif value == 'Plug':
                    gender = 'Male'
                else:
                    raise RuntimeError

        if label == 'Solar Connector Style':
            if gender:
                continue

            values = feature.get('primaryValues', [])
            if values:
                value = values[0].get('value', '')
                if value in ('Socket', 'Plug-Socket'):
                    gender = 'Female'
                elif value in ('Plug', 'Piercing'):
                    gender = 'Male'
                else:
                    raise RuntimeError

        if label == 'Connector Height':
            if height:
                continue

            values = feature.get('primaryValues', [])
            if values:
                height = float(values[0].get('value', '0.0'))

        if label == 'Product Height':
            if height:
                continue

            values = feature.get('primaryValues', [])
            if values:
                height = float(values[0].get('value', '0.0'))

        if label == 'Housing Color':
            if color:
                continue

            values = feature.get('primaryValues', [])
            if values:
                color = values[0].get('value', None)

        if label == 'Assembly Length':
            if length:
                continue

            values = feature.get('primaryValues', [])
            if values:
                length = float(values[0].get('value', '0.0'))

        if label == 'Primary Product Color':
            if color:
                continue

            values = feature.get('primaryValues', [])
            if values:
                color = values[0].get('value', None)

        if label == 'IP Rating':
            values = feature.get('primaryValues', [])
            if values:
                ip_rating = values[0].get('value', 'IP00')

        if label == 'Connector Shape':
            if shape:
                continue

            values = feature.get('primaryValues', [])
            if values:
                shape = values[0].get('value', None)

    for fg in product.get('featureGroups', []):
        label = fg.get('label', '')

        if label == 'Mechanical Attachment':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Mating Retention Type':
                    if cpa_lock_type:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        cpa_lock_type = values[0].get('value', None)

        if label == 'Contact Features':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Contact Size':
                    for value in feature.get('primaryValues', []):
                        value = get_terminal_size(value['value'])
                        if value is None:
                            continue

                        terminal_sizes.append(value)

        if label == 'Body Features':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Product Weight':
                    if weight:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        weight = float(values[0].get('value', '0.0'))

                if label2 == 'Seal Type':
                    if seal_type:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        seal_type = values[0].get('value', None)

        if label == 'Product Type Fetures':

            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Connector Seal & Plug Type':
                    if seal_type:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        seal_type = values[0].get('value', None)

        if label == 'Dimensions':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Connector Length':
                    if length:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        length = float(values[0].get('value', '0.0'))

                if label2 == 'Connector Height':
                    if height:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        height = float(values[0].get('value', '0.0'))

                if label2 == 'Connector Width':
                    if width:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        width = float(values[0].get('value', '0.0'))

                if label2 == 'Assembly Length':
                    if length:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        length = float(values[0].get('value', '0.0'))

                if label2 == 'Product Width':
                    if width:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        width = float(values[0].get('value', '0.0'))

                if label2 == 'Product Length':
                    if length:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        length = float(values[0].get('value', '0.0'))

                if label2 == 'Product Height':
                    if height:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        height = float(values[0].get('value', '0.0'))

                if label2 == 'Product Diameter':
                    values = feature.get('primaryValues', [])
                    if values:
                        width = height = float(values[0].get('value', '0.0'))

    if skip:
        continue

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

    if direction is None:
        direction = 'Straight'

    if gender is None:
        gender = 'Unknown'

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
        direction=direction,
        gender=gender,
        cavity_lock=cavity_lock,
        ip_rating=ip_rating,
        seal_type=seal_type,
        cpa_lock_type=cpa_lock_type,
        sealing=sealing,
        rows=rows,
        num_pins=num_pins,
        terminal_sizes=terminal_sizes,
        terminal_size_counts=terminal_size_counts,
        centerline=centerline,
        compat_cpas=compat_cpas,
        compat_tpas=compat_tpas,
        compat_covers=compat_covers,
        compat_terminals=compat_terminals,
        compat_seals=compat_seals,
        compat_housings=compat_housings,
        compat_boots=compat_boots,
        length=length,
        width=width,
        height=height,
        weight=weight,
        cover_point3d=None,
        seal_point3d=None,
        boot_point3d=None,
        tpa_lock_1_point3d=None,
        tpa_lock_2_point3d=None,
        cpa_lock_point3d=None
    ))

    if model3d is not None:
        model3d_count += 1

with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


print(len(out_data))
print(model3d_count)

