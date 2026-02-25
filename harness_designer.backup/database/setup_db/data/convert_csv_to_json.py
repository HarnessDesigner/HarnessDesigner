
def read_csv(line):
    res = []
    item = ''
    quote = False

    for char in line:
        if char == '"':
            quote = not quote
            continue

        if char == ',' and not quote:
            res.append(item)
            item = ''
            continue

        item += char

    res.append(item)

    for i, item in enumerate(res):
        if item.isdigit():
            item = int(item)

        else:
            try:
                item = float(item)
            except:  # NOQA
                pass

        res[i] = item

    return res


def tpa_locks():
    with open(r'tpa_locks.csv', 'r') as f:
        data = f.read().split('\n')

    out_data = []

    for line in data:
        (part_number, mfg, family, series, pins, color, min_temp, max_temp,
         length, width, height, terminal_size, image_path, cad_path) = read_csv(line)

        out_data.append(
            dict(
                part_number=str(part_number),
                mfg=mfg,
                series=str(series),
                family=str(family),
                length=float(length),
                width=float(width),
                height=float(height),
                color=str(color).title(),
                pins=str(pins),
                terminal_size=float(terminal_size),
                min_temp=int(min_temp),
                max_temp=int(max_temp),
                image=str(image_path),
                cad=str(cad_path)
            )
        )
    with open('tpa_locks.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


def cpa_locks():
    with open(r'cpa_locks.csv', 'r') as f:
        data = f.read().split('\n')

    out_data = []

    for line in data:
        (part_number, mfg, family, series, pins, color, min_temp, max_temp,
         length, width, height, terminal_size, image_path, cad_path) = read_csv(line)

        out_data.append(dict(
            part_number=str(part_number),
            mfg=mfg,
            series=str(series),
            family=str(family),
            length=float(length),
            width=float(width),
            height=float(height),
            color=str(color).title(),
            pins=str(pins),
            terminal_size=float(terminal_size),
            min_temp=int(min_temp),
            max_temp=int(max_temp),
            image=str(image_path),
            cad=str(cad_path)
        ))
    with open('cpa_locks.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


def seals():
    with open(r'seals.csv', 'r') as f:
        data = f.read().split('\n')
        
    out_data = []

    for line in data:
        l_data = read_csv(line)
        try:
            (part_number, mfg, series, type_, hardness, color, lubricant, min_temp,
             max_temp, length, o_dia, i_dia, wire_dia_min, wire_dia_max, image_path,
             cad_path) = l_data
        except:  # NOQA
            print(l_data)
            raise

        out_data.append(dict(
            part_number=str(part_number),
            mfg=str(mfg),
            series=str(series),
            type=str(type_),
            length=float(length),
            o_dia=float(o_dia),
            i_dia=float(i_dia),
            color=str(color),
            hardness=int(hardness),
            lubricant=str(lubricant),
            wire_dia_min=float(wire_dia_min),
            wire_dia_max=float(wire_dia_max),
            min_temp=int(min_temp),
            max_temp=int(max_temp),
            image=str(image_path),
            cad=str(cad_path)
        ))

    with open('seals.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


def covers():

    with open(r'covers.csv', 'r') as f:
        data = f.read().split('\n')

    out_data = []

    for line in data:
        (part_number, mfg, series, direction, length, width, height, min_temp,
         max_temp, pins, color, image_path, cad_path) = read_csv(line)

        out_data.append(dict(
            part_number=str(part_number),
            mfg=str(mfg),
            series=str(series),
            length=float(length),
            width=float(width),
            height=float(height),
            color=str(color).title(),
            pins=str(pins),
            direction=str(direction).title(),
            min_temp=int(min_temp),
            max_temp=int(max_temp),
            image=str(image_path),
            cad=str(cad_path)
        ))
        
    with open('covers.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


def terminals():
    with open(r'terminals.csv', 'r') as f:
        data = f.read().split('\n')
        
    out_data = []

    for line in data:
        l_data = read_csv(line)
        try:
            (part_number, mfg, family, series, min_wire_cross, max_wire_cross,
             gender, _, material, sealed, _, _, wire_dia_min, wire_dia_max, _,
             lock_type,  blade_size, _, _, _, _, _, _, image_path, cad_path) = l_data
        except:  # NOQA
            print(l_data)
            raise

        part_number = str(part_number)
        lock_type = str(lock_type)

        if not wire_dia_min:
            wire_dia_min = '0.0'

        if not wire_dia_max:
            wire_dia_max = '0.0'

        if not min_wire_cross:
            min_wire_cross = '0.0'

        if not max_wire_cross:
            max_wire_cross = '0.0'

        if not blade_size:
            blade_size = '0.0'

        wire_dia_min = float(wire_dia_min)
        wire_dia_max = float(wire_dia_max)
        min_wire_cross = float(min_wire_cross)
        max_wire_cross = float(max_wire_cross)
        series = str(series)
        gender = str(gender)
        image_path = str(image_path)
        cad_path = str(cad_path)
        blade_size = float(blade_size)
        sealed = str(sealed)
        if sealed == 'yes':
            sealing = 1
        else:
            sealing = 0

        out_data.append(dict(
            part_number=part_number,
            mfg=str(mfg),
            cavity_lock=lock_type.title(),
            wire_dia_min=wire_dia_min,
            wire_dia_max=wire_dia_max,
            min_wire_cross=min_wire_cross,
            max_wire_cross=max_wire_cross,
            series=series,
            gender=gender.title(),
            image=image_path,
            cad=cad_path,
            blade_size=blade_size,
            sealing=sealing,
            plating=str(material).title()
        ))
    
    with open('terminals.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


import json  # NOQA


def housings():
    with open(r'housings.csv', 'r') as f:
        data = f.read().split('\n')

    out_data = []

    for line in data:
        l_data = read_csv(line)
        try:
            (part_number, mfg, family, series, num_pins, rows, centerline, gender,
             cable_exit, color, sealing, min_temp, max_temp, length, width, height,
             terminal_lock, terminal_sizes, compat_terminals, compat_seals,
             compat_covers, compat_cpas, compat_tpas, mates_to, image_path,
             cad_path) = l_data
        except:  # NOQA
            print(l_data)
            raise

        part_number = str(part_number)
        mfg = str(mfg)
        family = str(family)
        series = str(series)

        if not num_pins:
            num_pins = '0'

        num_pins = int(num_pins)

        if not rows:
            rows = '0'

        rows = int(rows)

        if not centerline:
            centerline = '0.0'

        centerline = float(centerline)

        gender = str(gender).title()

        if cable_exit == 180:
            cable_exit = 'Straight'
        elif cable_exit == 270:
            cable_exit = 'Left'
        elif cable_exit == 90:
            cable_exit = 'Right'
        else:
            cable_exit = 'Straight'

        direction = cable_exit

        color = str(color).title()

        sealing = str(sealing).lower()

        if sealing == 'sealed':
            sealed = 1
        else:
            sealed = 0

        if not min_temp:
            min_temp = 0

        if not max_temp:
            max_temp = 0

        min_temp = int(min_temp)
        max_temp = int(max_temp)

        if not length:
            length = '0.0'

        length = float(length)

        if not width:
            width = '0.0'

        width = float(width)

        if not height:
            height = '0.0'

        height = float(height)

        cavity_lock = str(terminal_lock).title()

        if isinstance(terminal_sizes, (int, float)):
            terminal_sizes = str(float(terminal_sizes))

        terminal_sizes = [item.strip() for item in str(terminal_sizes).split(',')]
        terminal_sizes = ', '.join(terminal_sizes)
        terminal_sizes = f'[{terminal_sizes}]'

        if not mates_to:
            mates_to = '[]'

        if not compat_terminals:
            compat_terminals = '[]'

        if not compat_seals:
            compat_seals = '[]'

        if not compat_covers:
            compat_covers = '[]'

        if not compat_cpas:
            compat_cpas = '[]'

        if not compat_tpas:
            compat_tpas = '[]'

        cad = cad_path
        image = image_path

        out_data.append(dict(
            part_number=part_number,
            mfg=mfg,
            family=family,
            series=series,
            num_pins=num_pins,
            rows=rows,
            centerline=centerline,
            gender=gender,
            direction=direction,
            color=color,
            sealed=sealed,
            min_temp=min_temp,
            max_temp=max_temp,
            length=length,
            width=width,
            height=height,
            cavity_lock=cavity_lock,
            terminal_sizes=terminal_sizes,
            mates_to=mates_to,
            compat_terminals=compat_terminals,
            compat_seals=compat_seals,
            compat_covers=compat_covers,
            compat_cpas=compat_cpas,
            compat_tpas=compat_tpas,
            cad=cad,
            image=image
        ))

    with open('housings.json', 'w') as f:
        f.write(json.dumps(out_data, indent=4))


if __name__ == '__main__':
    terminals()
    covers()
    seals()
    cpa_locks()
    tpa_locks()
