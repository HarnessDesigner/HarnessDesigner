




'''



SEALS ================

                'hardness INTEGER DEFAULT -1 NOT NULL, '
                'lubricant TEXT DEFAULT "" NOT NULL, '
                'length REAL DEFAULT "0.0" NOT NULL, '
                'o_dia REAL DEFAULT "0.0" NOT NULL, '
                'i_dia REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_min REAL DEFAULT "0.0" NOT NULL, '
                'wire_dia_max REAL DEFAULT "0.0" NOT NULL, '
                'weight REAL DEFAULT "0.0" NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL, '










    Manufacturer
        'Bosch'

    color = convert_color(specs.get('Colour', None))
    Colour
        'nature'
        'white'

    length = convert_dimension(specs.get('Length', None))
    Length
        '3.9mm'

    width = convert_dimension(specs.get('Width', None))
    Width
        '3.9mm'

    height = convert_dimension(specs.get('Height', None))
    Height
        '7.8mm'

    min_temp = convert_temperature(specs.get('Temperature range, min.', None))
    Temperature range, min.
        '-40°'

    min_temp = convert_temperature(specs.get('Temperature range, min.', None))
    Temperature range, max.
        '125°'



    Manufacturer
        'Bosch'

    color = convert_color(specs.get('Colour', None))
    Colour
        'blue'
        'green'
        'grey'
        'red'
        'red-brown'
        'white'
        'yellow'

    length = convert_dimension(specs.get('Length', None))
    Length
        '3.9mm'
        '5.65mm'
        '9mm'

    width = convert_dimension(specs.get('Width', None))
    Width
        '3.9mm'
        '5.65mm'
        '9mm'

    height = convert_dimension(specs.get('Height', None))
    Height
        '7.8mm'

    min_temp = convert_temperature(specs.get('Temperature range, min.', None))
    Temperature range, min.
        '-40°'

    max_temp = convert_temperature(specs.get('Temperature range, max.', None))
    Temperature range, max.
        '125°'


ACCESSORY ====================
                'part_number TEXT UNIQUE NOT NULL, '
                'description TEXT DEFAULT "" NOT NULL, '
                'mfg_id INTEGER DEFAULT 0 NOT NULL, '
                'family_id INTEGER DEFAULT 0 NOT NULL, '
                'series_id INTEGER DEFAULT 0 NOT NULL, '
                'color_id INTEGER DEFAULT NULL, '
                'material_id INTEGER DEFAULT 0 NOT NULL, '
                'model3d_id INTEGER DEFAULT NULL,'


Accessories
    Manufacturer
        'Bosch'

    color = convert_color(specs.get('Colour', None))
    Colour
        'black'
        'grey'
        'nature'

    length = convert_dimension(specs.get('Length', None))
    Length
        '100mm'
        '12mm'
        '17.75mm'
        '22.5mm'
        '34.2mm'
        '3mm'

    width = convert_dimension(specs.get('Width', None))
    Width
        '13.8mm'
        '17mm'
        '19mm'
        '33mm'
        '3mm'

    height = convert_dimension(specs.get('Height', None))
    Height
        '0.4mm'
        '11.5mm'
        '14mm'
        '6.5mm'
        '8mm'

    RoHS
        'Yes'

    Body Material
        'LSR'
        'PA 66 GF'
        'PA 66 GF 30'
        'PA 66 GF 50'
        'Silikon Shore A40'

    Secondary locking
        'none'

    Additional features
        'cross recess'

    Connection System
        'Wire-to-Device'

    min_temp = convert_temperature(specs.get('Temperature range, min.', None))
    Temperature range, min.
        '-40°'

    max_temp = convert_temperature(specs.get('Temperature range, max.', None))
    Temperature range, max.
        '85°'




UNUSED =========================



Crimping Plier
    Manufacturer
        'Bosch'

    Wire cross section
        '&gt;0.5 / 0.75 / 0.85'
        '0,35 - 0,5'
        '0,75 - 1,0'
        '0.35 - 0.5'
        '0.35 / 0.5'
        '0.35 / 0.5 / 0.75'
        '0.5 - 1'
        '0.5 - 1.0'
        '0.5; 0.75; 1'
        '0.75 / 1.0'
        '1,5'
        '1.5 - 2.5'
        '1.5; 2.5'



Crimping Tool
    Manufacturer
        'Bosch'

    Wire cross section
        '0.3 - 0.5'
        '0.35 - 0.5'
        '0.35 - 0.50'
        '0.35 – 0.50'
        '0.5 - 0.75'
        '0.5 - 1'
        '0.5 - 1.0'
        '0.61'
        '0.75'
        '0.75 / 0.85'
        '1'
        '1.5 - 2.5'
        '1.50'

    Raster unit
        'on carrier strip 11.8mm'
        'on carrier strip 8mm'



Disassembling Tool
    Manufacturer
        'Bosch'

    Colour
        'black'

    Length
        '79.6mm'

    Width
        '20.7mm'

    Height
        '20.7mm'

    Wire cross section
        '0.35…0.75'
        '0.75…2.5'

    Raster unit
        '2.5mm'
        '4.5mm'

    Row distance
        '3.5mm'
        '4.3mm'

    Line voltage from
        '20'

    Current-carrying capacity
        'max. 3 A'
        'max. 7 A'



'''