from typing import TYPE_CHECKING

import wx
import math
import weakref

from . import ObjectBase as _ObjectBase
from ..wrappers.decimal import Decimal as _decimal
from ..wrappers import color as _color
from ..geometry import line as _line


if TYPE_CHECKING:
    from .. import ui as _ui
    from ..database.project_db import pjt_wire as _pjt_wire
    from ..database.project_db import pjt_circuit as _pjt_circuit


class WireInfoMeta(type):
    _instances = {}

    @staticmethod
    def _remove_ref(ref):
        for key in list(WireInfoMeta._instances.keys()):
            if ref == WireInfoMeta._instances[key]:
                del WireInfoMeta._instances[key]
                break

    def __call__(cls, circuit: "Circuit", db_obj: "_pjt_wire.PJTWire"):
        key = (circuit.id, db_obj.db_id)
        if key in WireInfoMeta._instances:
            instance = WireInfoMeta._instances[key]()

            if instance is not None:
                return instance

        instance = super().__call__(circuit, db_obj)
        WireInfoMeta._instances[key] = weakref.ref(instance, cls._remove_ref)

        return instance


class WireInfo(metaclass=WireInfoMeta):

    def __init__(self, circuit: "Circuit", db_obj: "_pjt_wire.PJTWire"):
        self._circuit = circuit
        self._db_obj = db_obj
        self._part = db_obj.part

    @property
    def color(self) -> _color.Color:
        return self._part.color.ui

    @property
    def stripe_color(self) -> _color.Color | None:
        color = self._part.stripe_color

        if color is not None:
            return color.ui

    @property
    def num_conductors(self) -> int:
        return self._part.num_conductors

    @property
    def is_shielded(self) -> bool:
        return self._part.shielded

    @property
    def od_mm(self) -> _decimal:
        return self._part.od_mm

    def __eq__(self, other):
        if not isinstance(other, WireInfo):
            return False

        return other.awg == self.awg and other.num_conductors == self.num_conductors and other.is_shielded == self.is_shielded

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg > self.awg and other.num_conductors <= self.num_conductors

    def __lt__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg < self.awg and other.num_conductors >= self.num_conductors

    def __ge__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg >= self.awg and other.num_conductors <= self.num_conductors

    def __le__(self, other):
        if not isinstance(other, WireInfo):
            raise RuntimeError

        return other.awg <= self.awg and other.num_conductors >= self.num_conductors

    @property
    def length_m(self) -> _decimal:
        line = _line.Line(self._db_obj.start_point3d, self._db_obj.stop_point3d)
        return line.length() / _decimal(1000.0)

    @property
    def length_ft(self) -> _decimal:
        return self.length_m * _decimal(3.28084)

    @property
    def recommended_mm2(self):
        awg, _ = self.recommended_awg
        if awg is None:
            return None

        return self.__awg_to_mm2(awg)

    @staticmethod
    def __awg_to_mm2(awg: int) -> _decimal:
        d_in = _decimal(0.005) * (_decimal(92) ** ((_decimal(36) - _decimal(awg)) / _decimal(39)))
        d_mm = d_in * _decimal(25.4)
        area_mm2 = (_decimal(math.pi) / _decimal(4)) * (d_mm ** _decimal(2))
        return round(area_mm2, 4)

    @property
    def recommended_awg(self):
        # TODO: write D.R.T. (Design Rules Tester)
        #       DRT will check the circuits to make sure that wire sizes
        #       will support the load that has been entered by the user.
        #       This feature depends on the proper resistance values being
        #       entered for the wires and also the voltage being entered for
        #       the start of the circuit.
        #       This feature will be a complicated feature to add because of
        #       handling circuits as seen below.

        #    e_t1-----
        #             | splice -------- s_t
        #    e_t2-----             ^
        #          ^               |
        #          |       calculate wire size which will be larger
        #          |       than the branches
        #          |
        #      calculate wire size which is going to be smaller
        #      that what is needed for the "trunk"


        total_wire_length = self._db_obj.circuit.wire_length_m

        resistances = [wire_info.resistance
                       for wire_info in self.circuit.wire_info
                       if wire_info != self]

        # total_resistance =
        #
        # load = self.load
        # v_drop = self.voltage_drop
        # awg = self.awg
        #
        # db_ids = self._part._table.select(  # NOQA
        #     'db_id', series_id=self._part.series_id)
        #
        # available_wires = [self._part._table[db_id[0]] for db_id in db_ids]  # NOQA
        # available_awgs = [wire.size_awg for wire in available_wires]
        # allowed_drop = self.allowed_voltage_drop
        #
        # while awg != -1 and v_drop > allowed_drop:
        #     awg -= 1
        #     if awg not in available_awgs:
        #         continue
        #
        #     index = available_awgs.index(awg)
        #     wire = available_wires[index]
        #     resistance = wire.resistance_1km
        #     resistance /= _decimal(1000)
        #     resistance *= total_wire_length
        #     v_drop = _decimal(2.0) * load * resistance
        #
        # if awg != -1:
        #     double_c_weight = self._part.weight_g_m * _decimal(2.0)
        #
        #     index = available_awgs.index(awg)
        #     wire = available_wires[index]
        #
        #     if wire.weight_g_m >= double_c_weight:
        #         weight_savings = ((total_wire_length * wire.weight_g_m) -
        #                           (total_wire_length * double_c_weight))
        #
        #         message = (f'Adding a second conductor will have\n'
        #                    f'a weight savings of {weight_savings} grams')
        #     else:
        #         message = ''
        # else:
        #     message = ('Larger wire in the same series is\n'
        #                'not available that will carry the current.')
        #
        # if awg == -1:
        #     awg = None
        #
        # return awg, message

    @property
    def circuit(self) -> "Circuit":
        return self._circuit

    @property
    def all_loads(self) -> list[list[str, _decimal]]:
        res = [[terminal.cavity.name, terminal.load]
               for terminal in self._db_obj.circuit.terminals
               if not terminal.is_start]

        return res

    @all_loads.setter
    def all_loads(self, values: list[list[str, float]]):
        terminals = [t for t in self._db_obj.circuit.terminals if not t.is_start]

        for name, load in values:
            for terminal in terminals:
                if terminal.cavity.name == name:
                    terminal.load = _decimal(load)
                    break
    @property
    def loads(self) -> list[list[str, _decimal]]:
        res = [[terminal.cavity.name, terminal.load]
               for terminal in self._db_obj.circuit.get_circuit_end_terminals(self._db_obj)]

        return res

    @loads.setter
    def loads(self, values: list[list[str, float]]):
        terminals = [t for t in self._db_obj.circuit.get_circuit_end_terminals(self._db_obj)]

        for name, load in values:
            for terminal in terminals:
                if terminal.cavity.name == name:
                    terminal.load = _decimal(load)
                    break

    @property
    def volts(self) -> _decimal:
        return self._db_obj.circuit.start_terminal.volts

    @volts.setter
    def volts(self, value: float):
        self._db_obj.circuit.start_terminal.volts = _decimal(value)

    @property
    def resistance_up_to(self) -> _decimal:

        def _iter_map(objs):
            r = _decimal(0.0)
            for obj in objs:
                if isinstance(obj, list):
                    r += _iter_map(obj)
                else:
                    r += obj.resistance

            return r

        circuit_map = self._db_obj.circuit.get_circuit(self._db_obj)

        resistance = _iter_map(circuit_map)
        return resistance

    @property
    def load_up_to(self) -> _decimal:
        circuit = self._db_obj.circuit
        start_terminal = circuit.start_terminal
        end_terminals = circuit.get_circuit_end_terminals(self._db_obj)

        volts = start_terminal.volts
        if end_terminals:
            current = sum([t.load for t in end_terminals])
        else:
            current = _decimal(0.0)

        # current = voltage / resistance
        current += volts / self.resistance_up_to

        return current

    @property
    def resistance_1km(self) -> _decimal:
        return self._part.resistance_1km

    @property
    def resistance_1kft(self) -> _decimal:
        return self._part.resistance_1kft

    @property
    def resistance_ft(self) -> _decimal:
        return self._part.resistance_ft

    @property
    def resistance_m(self) -> _decimal:
        return self._part.resistance_m

    @property
    def resistance(self) -> _decimal:
        res_per_foot = self._part.resistance_ft
        return self.length_ft * res_per_foot

    @property
    def weight_1kft(self) -> _decimal:
        return self._part.weight_1kft

    @property
    def weight_lb_ft(self) -> _decimal:
        return self._part.weight_lb_ft

    @property
    def weight_1km(self) -> _decimal:
        return self._part.weight_1km

    @property
    def weight_g_m(self) -> _decimal:
        return self._part.weight_g_m

    @property
    def weight_g_ft(self) -> _decimal:
        return self._part.weight_g_ft

    @property
    def allowed_voltage_drops(self) -> _decimal:
        return self._db_obj.circuit

    @allowed_voltage_drops.setter
    def allowed_voltage_drops(self, value: float):
        self._db_obj.circuit.voltage_drop = _decimal(value)

    @property
    def voltage_drop(self) -> _decimal:
        return (_decimal(2.0) * self.resistance * self.load) / _decimal(self.num_conductors)

    @property
    def conductivity_symbol(self) -> str:
        return 'S/m'

    @property
    def conductivity(self):
        raise NotImplementedError

    @property
    def resistivity_symbol(self) -> str:
        return 'Ω/m'

    @property
    def resistivity(self) -> float:
        """
        The nominal resistance of a wire can be calculated using the following
        wire resistance equation, where:

            ρ = Resistivity
            l = Wire length
            A = Cross-sectional area

            Resistance (Ohms) = (ρ x l) / A

        However, as resistivity and size units can be varied (Ω.m, µΩ.cm etc)
        for a round wire the following resistance of wire formula can be used:

            ρ = Resistivity in µΩ.cm
            l = Wire length in m
            d = Solid Wire diameter in mm

            Resistance (Ohms) = (ρ x l) / (25 x π x d²)
        """
        raise NotImplementedError

    @property
    def material(self) -> str:
        return self._part.material.name

    @property
    def core_material_symbol(self) -> str:
        return self._part.core_material.symbol

    @property
    def core_material_description(self) -> str:
        return self._part.core_material.description

    @property
    def mm2(self) -> _decimal:
        return self._part.size_mm2

    @property
    def in2(self) -> _decimal:
        return self._part.size_in2

    @property
    def awg(self) -> int:
        return self._part.size_awg

    @property
    def diameter_in(self) -> _decimal:
        return self._part.conductor_dia_in

    @property
    def diameter_mm(self) -> _decimal:
        return self._part.conductor_dia_mm

    @property
    def pixel_width(self):
        width_map = {
            30: 1, 29: 1, 28: 1, 27: 2, 26: 2, 25: 2, 24: 3, 23: 3, 22: 3,
            21: 4, 20: 4, 19: 4, 18: 5, 17: 5, 16: 5, 15: 5, 14: 6, 13: 6,
            12: 6, 11: 7, 10: 7, 9: 7, 8: 8, 7: 8, 6: 8, 5: 9, 4: 9,
            3: 9, 2: 10, 1: 10, 0: 10
        }

        awg = self.awg

        if awg not in width_map:
            raise RuntimeError('sanity check')

        return width_map[awg]


class HSizer(wx.BoxSizer):

    def __init__(self, parent, text, ctrl, suffix=None, in_panel=False):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)

        if in_panel:
            panel = wx.Panel(parent, wx.ID_ANY, style=wx.BORDER_NONE)
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            if text is not None:
                st = wx.StaticText(panel, wx.ID_ANY, label=text)
                sizer.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            ctrl.Reparent(panel)
            sizer.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            if isinstance(suffix, str):
                suffix = wx.StaticText(panel, wx.ID_ANY, label=suffix)
                sizer.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)
            elif suffix is not None:
                suffix.Reparent(panel)
                sizer.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)

            panel.SetSizer(sizer)
            self.Add(panel, 0)

        else:
            if text is not None:
                st = wx.StaticText(parent, wx.ID_ANY, label=text)
                self.Add(st, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            self.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)

            if isinstance(suffix, str):
                suffix = wx.StaticText(parent, wx.ID_ANY, label=suffix)

            if suffix is not None:
                self.Add(suffix, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, 5)


class WireInfoPanel(wx.Panel):

    def on_volts(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.volts = value
        self.update_wire_length()
        evt.Skip()

    def on_volt_drop(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.allowed_voltage_drop = value
        self.update_wire_length()
        evt.Skip()

    def on_load(self, evt: wx.SpinDoubleEvent):
        value = evt.GetValue()
        self.wire_info.load = value
        self.update_wire_length()
        evt.Skip()

    def update_editor(self):
        def _do():
            self.GetParent().update_bitmap()
            self.GetParent().Update()
            self.GetParent().Refresh()

        wx.CallAfter(_do)

    def update_wire_length(self):
        self.length_ft_ctrl.SetLabel(str(round(self.wire_info.length_ft, 4)))
        self.length_m_ctrl.SetLabel(str(round(self.wire_info.length_m, 4)))
        self.length_cm_ctrl.SetLabel(str(round(self.wire_info.length_m * _decimal(100.0), 4)))
        self.voltage_drop_ctrl.SetLabel(str(round(self.wire_info.voltage_drop, 2)))

        awg, message = self.wire_info.recommended_awg

        self.recommended_awg_ctrl.SetLabel(str(awg))
        self.recommended_awg_msg_ctrl.SetLabel(message)

        mm2 = self.wire_info.recommended_mm2
        if mm2 is None:
            self.recommended_mm2_ctrl.SetLabel(str(mm2))
        else:
            self.recommended_mm2_ctrl.SetLabel(str(round(mm2, 4)))

        self.weight_lb_ctrl.SetLabel(str(round(self.wire_info.circuit.wire_weight_lb, 4)))
        self.weight_kg_ctrl.SetLabel(str(round(self.wire_info.circuit.wire_weight_g / _decimal(1000), 4)))
        self.resistance_ctrl.SetLabel(str(round(self.wire_info.resistance, 4)))

    def update_wire(self):
        if self.wire_info is None:
            return

        self.set_wire(self.wire_info)

    def set_wire(self, wi: WireInfo):
        self.material_ctrl.SetLabel(wi.material)
        self.shielded_ctrl.SetLabel('Yes' if wi.is_shielded else 'No')
        self.volts_ctrl.SetValue(wi.volts)
        self.volt_drop_ctrl.SetValue(wi.allowed_voltage_drop)
        self.conductor_ctrl.SetLabel(str(wi.num_conductors))
        self.awg_ctrl.SetLabel(str(wi.awg))
        self.mm2_ctrl.SetLabel(str(wi.mm2))
        self.od_mm_ctrl.SetLabel(str(round(wi.od_mm, 4)))
        self.voltage_drop_ctrl.SetLabel(str(round(wi.voltage_drop, 2)))

        awg, message = wi.recommended_awg
        self.recommended_awg_ctrl.SetLabel(str(awg))
        self.recommended_awg_msg_ctrl.SetLabel(message)

        mm2 = wi.recommended_mm2
        if mm2 is None:
            self.recommended_mm2_ctrl.SetLabel(str(mm2))
        else:
            self.recommended_mm2_ctrl.SetLabel(str(round(mm2, 4)))

        self.diameter_mm_ctrl.SetLabel(str(round(wi.diameter_mm, 4)))
        self.diameter_inch_ctrl.SetLabel(str(round(wi.diameter_in, 4)))
        self.in2_ctrl.SetLabel(str(round(wi.in2, 4)))

        length = wi.circuit.wire_length_m
        self.length_m_ctrl.SetLabel(str(round(length, 4)))
        self.length_cm_ctrl.SetLabel(str(round(length * _decimal(100.0), 4)))
        self.length_ft_ctrl.SetLabel(str(round(wi.length_ft, 4)))

        self.weight_lb_ctrl.SetLabel(str(round(wi.circuit.wire_weight_lb, 4)))
        self.weight_kg_ctrl.SetLabel(str(round(wi.circuit.wire_weight_g, 4)))

        self.resistance_ctrl.SetLabel(str(round(wi.resistance, 4)))
        self.color1_ctrl.SetBackgroundColour(wi.color)

        stripe = wi.stripe_color
        if stripe is not None:
            self.color2_ctrl.SetBackgroundColour(stripe)
        else:
            self.color2_ctrl.SetBackgroundColour(self.GetBackgroundColour())

        self.wire_info = wi

    def __init__(self, parent):

        wx.Panel.__init__(self, parent, wx.ID_ANY)
        self.wire_info: WireInfo = None

        material_ctrl = self.material_ctrl = wx.StaticText(self, wx.ID_ANY, label='WWWWWWWWWWWWWWWW (WW/WW)')
        shielded_ctrl = self.shielded_ctrl = wx.StaticText(self, wx.ID_ANY, label='Yes')

        volts_ctrl = self.volts_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='12.0', min=3.3, max=240.0, initial=12.0, inc=0.1)
        volts_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_volts)

        load_ctrl = self.load_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=300.0, initial=0.0, inc=0.1)
        load_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_load)

        volt_drop_ctrl = self.volt_drop_ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, value='0.0', min=0.0, max=3.0, initial=0.0, inc=0.1)
        volt_drop_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_volt_drop)

        conductor_ctrl = self.conductor_ctrl = wx.StaticText(self, wx.ID_ANY, label='00')
        awg_ctrl = self.awg_ctrl = wx.StaticText(self, wx.ID_ANY, label='00')
        mm2_ctrl = self.mm2_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')

        color1_ctrl = self.color1_ctrl = wx.Panel(self, wx.ID_ANY, size=(75, 25), style=wx.BORDER_SUNKEN)
        color2_ctrl = self.color2_ctrl = wx.Panel(self, wx.ID_ANY, size=(75, 25), style=wx.BORDER_SUNKEN)

        od_mm_ctrl = self.od_mm_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        voltage_drop_ctrl = self.voltage_drop_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        recommended_awg_ctrl = self.recommended_awg_ctrl = wx.StaticText(self, wx.ID_ANY, label='00')
        recommended_mm2_ctrl = self.recommended_mm2_ctrl = wx.StaticText(self, wx.ID_ANY, label='00.0000')
        diameter_mm_ctrl = self.diameter_mm_ctrl = wx.StaticText(self, wx.ID_ANY, label='00.0000')
        diameter_inch_ctrl = self.diameter_inch_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        in2_ctrl = self.in2_ctrl = wx.StaticText(self, wx.ID_ANY, label='0.0000')
        length_ft_ctrl = self.length_ft_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        length_m_ctrl = self.length_m_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        length_cm_ctrl = self.length_cm_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        weight_lb_ctrl = self.weight_lb_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        weight_kg_ctrl = self.weight_kg_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')
        resistance_ctrl = self.resistance_ctrl = wx.StaticText(self, wx.ID_ANY, label='000.0000')

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddMany((
            (HSizer(self, 'Material:', material_ctrl), 0),
            (HSizer(self, 'Shielded:', shielded_ctrl), 0),
            (HSizer(self, 'Conductor Count:', conductor_ctrl), 0),
            (HSizer(self, 'Load:', load_ctrl, 'A'), 0),
            (HSizer(self, 'Length:', length_ft_ctrl, 'ft', in_panel=True), 0),
            (HSizer(self, 'Length:', length_m_ctrl, 'm', in_panel=True), 0),
            (HSizer(self, 'Length:', length_cm_ctrl, 'cm', in_panel=True), 0),
            (HSizer(self, 'Volts:', volts_ctrl, 'V'), 0),
            (HSizer(self, 'Max Drop:', volt_drop_ctrl, 'V'), 0),
            (HSizer(self, 'Actual Drop:', voltage_drop_ctrl, 'V', in_panel=True), 0),
            (HSizer(self, 'Size:', awg_ctrl, 'AWG'), 0),
            (HSizer(self, 'Size:', mm2_ctrl, 'mm²'), 0),
            (HSizer(self, 'Size:', in2_ctrl, 'in²'), 0),
            (HSizer(self, 'Primary Color:', color1_ctrl), 0),
            (HSizer(self, 'Stripe Color:', color2_ctrl), 0),
            (HSizer(self, 'Diameter (total):', od_mm_ctrl, 'mm'), 0),
            (HSizer(self, 'Recommended Size:', recommended_awg_ctrl, 'AWG', in_panel=True), 0),
            (HSizer(self, 'Recommended Size:', recommended_mm2_ctrl, 'mm²', in_panel=True), 0),
            (HSizer(self, 'Conductor Diameter:', diameter_mm_ctrl, 'mm'), 0),
            (HSizer(self, 'Conductor Diameter:', diameter_inch_ctrl, 'in'), 0),
            (HSizer(self, 'Weight:', weight_lb_ctrl, 'lb', in_panel=True), 0),
            (HSizer(self, 'Weight:', weight_kg_ctrl, 'kg', in_panel=True), 0),
            (HSizer(self, 'Resistance:', resistance_ctrl, 'Ω', in_panel=True), 0)
        ))

        self.SetSizer(sizer)


class Circuit(_ObjectBase):

    def __init__(self, mainframe: "_ui.MainFrame", db_obj: "_pjt_circuit.PJTCircuit"):
        super().__init__(mainframe)
        self._db_obj = db_obj


