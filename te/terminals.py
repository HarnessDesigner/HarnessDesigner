import json
import math

in_path = 'separated/terminals.json'
out_path = 'output/terminals.json'

te_url = 'https://api.te.com/'

with open(in_path, 'r') as f:
    in_data = json.loads(f.read())

out_data = []


def get_temperatures(val):
    if not val:
        return None, None

    val = val.split(' – ')
    if len(val) == 1:
        min_val = max_val = val[0]
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



from decimal import Decimal


def _d(v):
    try:
        return Decimal(str(v))
    except:
        print(repr(v))
        raise


def kcmil_to_mm2(kcmil):
    return float(round(_d(kcmil) * _d(0.5067), 4))


def awg_to_mm2(awg: int) -> float:
    if '#' in awg:
        awg = awg.replace('#', '')

    awg = awg.split('(', 1)[0].strip()

    mapping = {
        '4/0': 107,
        '3/0': 85.0,
        '2/0': 67.4,
        '1/0': 53.5
    }
    if awg in mapping:
        return mapping[awg]

    awg = int(float(awg))

    if awg >= 250:
        mm2 = kcmil_to_mm2(awg)
    else:
        d_in = _d(0.005) * (_d(92) ** ((_d(36) - _d(awg)) / _d(39)))
        d_mm = d_in * _d(25.4)
        mm2 = (_d(math.pi) / _d(4)) * (d_mm ** _d(2))

    return float(round(mm2, 4))


def mm2_to_awg(mm2: float) -> int:
    if mm2 >= 53.5:
        mapping = {
            53.5: -1,
            67.4: -2,
            85.0: -3,
            107.0: -4
        }
        if mm2 in mapping:
            return mapping[mm2]

        return int(round(_d(mm2) / _d(0.5067)))

    d_mm = _d(2.0) * _d(math.sqrt(_d(mm2) / _d(math.pi)))
    d_in = d_mm / _d(25.4)
    awg = _d(36) - _d(39) * _d(math.log(float(d_in / _d(0.005)), 92))
    return int(round(awg))


def awg_to_d_mm(awg: int) -> float:
    return mm2_to_d_mm(awg_to_mm2(awg))


def mm2_to_d_mm(mm2: float) -> float:
    d_mm = _d(2.0) * _d(math.sqrt(_d(mm2) / _d(math.pi)))
    return float(round(d_mm, 4))


def d_mm_to_mm2(d_mm: float) -> float:
    mm2 = _d(d_mm) / _d(2.0)
    mm2 *= mm2
    mm2 *= _d(math.pi)
    return float(round(mm2, 4))


def get_wire_size(val, unit='AWG'):
    if not val:
        return None, None

    if ' - ' in val:
        val = val.split(' - ')
    else:
        val = val.split(' – ')

    if len(val) == 1:
        min_val = max_val = val[0].strip()
    else:
        min_val, max_val = val

    if unit == 'AWG':
        return awg_to_mm2(min_val), awg_to_mm2(max_val)
    elif unit == 'mm':
        if min_val.startswith('.'):
            min_val = '0' + min_val

        if max_val.startswith('.'):
            max_val = '0' + max_val

        min_val = float(min_val)
        max_val = float(max_val)

        return d_mm_to_mm2(min_val), d_mm_to_mm2(max_val)

    elif unit == 'CMA':
        min_val = float(round(_d(0.0005067075) * _d(min_val), 4))
        max_val = float(round(_d(0.0005067075) * _d(max_val), 4))

        return min_val, max_val
    elif unit == 'mm²':
        try:
            min_val = float(round(_d(min_val), 4))
            max_val = float(round(_d(max_val), 4))
        except:
            print(repr(min_val), repr(max_val), repr(val))
            raise
        return min_val, max_val

    else:
        raise RuntimeError(uom)


def get_size(val, unit):
    val = val.replace('mm', '')

    if 'K' in val:
        return 0.0

    if unit == 'AWG':
        val = val.replace('Size', '').strip()
        val = val.split('(', 1)[0].strip()

        return awg_to_d_mm(val)

    if val.startswith('.'):
        val = '0' + val

    return float(val)


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

plating=None, 
gender=None, 
cavity_lock=None,
sealing=0, 
blade_size=0.0, 
resistance=0.0, 
mating_cycles=0, 
max_vibration_g=0,
max_current_ma=0, 

wire_size_min_awg=-1, 
wire_size_max_awg=-1, 

wire_dia_min=0.0,
wire_dia_max=0.0, 

min_wire_cross=0.0, 
max_wire_cross=0.0, 

length=0.0,
width=0.0, 
height=0.0, 
weight=0.0, 
compat_housings=None, 
compat_seals=None

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
    compat_seals = None

    plating = None  # *
    gender = None
    cavity_lock = None  # *
    sealing = 0  # *

    blade_size = 0.0
    resistance = 0.0
    mating_cycles = 0
    max_vibration_g = 0

    max_current_ma = 0  # *

    wire_size_min_awg = 0  # *
    wire_size_max_awg = 0  # *

    wire_dia_min = 0.0  # *
    wire_dia_max = 0.0  # *

    min_wire_cross = 0.0  # *
    max_wire_cross = 0.0  # *

    length = 0.0
    width = 0.0
    height = 0.0
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

        if label == 'Contact Retention Type Within Housing':
            if cavity_lock:
                continue

            values = feature.get('primaryValues', [])
            if values:
                cavity_lock = values[0].get('value', None)

        if label == 'Primary Locking Feature':
            if cavity_lock:
                continue

            values = feature.get('primaryValues', [])
            if values:
                cavity_lock = values[0].get('value', None)

        if label == 'Terminal Plating Material':
            if plating:
                continue

            values = feature.get('primaryValues', [])
            if values:
                plating = values[0].get('value', None)

        if label == 'Contact Base Material':
            if plating:
                continue

            values = feature.get('primaryValues', [])
            if values:
                plating = values[0].get('value', None)

        if label == 'Compatible Conductor Range':
            values = feature.get('primaryValues', [])
            if values:

                min_wire_cross, max_wire_cross = get_wire_size(values[0].get('value', ''))

                wire_dia_min = mm2_to_d_mm(min_wire_cross)
                wire_dia_max= mm2_to_d_mm(max_wire_cross)

                wire_size_min_awg = mm2_to_awg(min_wire_cross)
                wire_size_max_awg = mm2_to_awg(max_wire_cross)

        if label == 'Sealable':

            values = feature.get('primaryValues', [])
            if values:
                sealing = int(values[0].get('value', 'No') == 'Yes')

        if label == 'Contact Current Rating (Max)':
            if max_current_ma:
                continue

            values = feature.get('primaryValues', [])
            if values:
                max_current_ma = int(float(values[0].get('value', '0.0')) * 1000)



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

        if label == 'Product Height':
            if height:
                continue

            values = feature.get('primaryValues', [])
            if values:
                height = float(values[0].get('value', '0.0'))

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

    for fg in product.get('featureGroups', []):
        label = fg.get('label', '')

        if label == 'Contact Features':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Contact Size':
                    if blade_size:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        try:
                            uom = feature['primaryUnit']['code']
                        except KeyError:
                            uom = 'AWG'

                        blade_size = get_size(values[0].get('value', '0.0'), uom)

                if label2 in ('Contact Type', 'Terminal Type'):
                    if gender:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        value = values[0].get('value', None)

                        mapping = {
                            'Socket': 'Female',
                            'Pneumatic Plug': 'Male',
                            'Tab': 'Male',
                            'Pin': 'Male',
                            'Receptacle': 'Female',
                            'Blade': 'Male'
                        }

                        gender = mapping.get(value, None)

                if label2 == 'Contact Length':
                    if length:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        length = float(values[0].get('value', '0.0'))

                if label2 == 'Contact Diameter':
                    if length:
                        continue

                    values = feature.get('primaryValues', [])
                    if values:
                        width = height = float(values[0].get('value', '0.0'))

        if label == 'Dimensions':
            for feature in fg.get('features', []):
                label2 = feature.get('label', '')

                if label2 == 'Wire Size':
                    values = feature.get('primaryValues', [])
                    if values:

                        uom = feature['primaryUnit']['code']

                        min_wire_cross, max_wire_cross = get_wire_size(values[0].get('value', ''), uom)

                        wire_dia_min = mm2_to_d_mm(min_wire_cross)
                        wire_dia_max = mm2_to_d_mm(max_wire_cross)

                        wire_size_min_awg = mm2_to_awg(min_wire_cross)
                        wire_size_max_awg = mm2_to_awg(max_wire_cross)

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
        plating=plating,
        gender=gender,
        cavity_lock=cavity_lock,
        sealing=sealing,
        blade_size=blade_size,
        resistance=resistance,
        mating_cycles=mating_cycles,
        max_vibration_g=max_vibration_g,
        max_current_ma=max_current_ma,
        wire_size_min_awg=wire_size_min_awg,
        wire_size_max_awg=wire_size_max_awg,
        wire_dia_min=wire_dia_min,
        wire_dia_max=wire_dia_max,
        min_wire_cross=min_wire_cross,
        max_wire_cross=max_wire_cross,
        length=length,
        width=width,
        height=height,
        weight=weight,
        compat_housings=compat_housings,
        compat_seals=compat_seals
    ))

    if model3d is not None:
        model3d_count += 1


with open(out_path, 'w') as f:
    f.write(json.dumps(out_data, indent=4))


print(len(out_data))
print(model3d_count)



