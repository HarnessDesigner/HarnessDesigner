# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Global-DB classes for ``wire_conductors``.

The individual conductors inside a multi-conductor wire, one row per conductor. :class:`WireConductor` is a catalog row like
:class:`~.wire.Wire`, and it answers the same questions a ``Wire`` does (colour, stripe colour, size, ``od_mm``, resistance,
materials, weights ...), so code that is handed a wire's ``part`` works the same when the part is one conductor of a cable: a
placed cable's conductor (and the lead wires that come out of it) has this row as its ``part``. Anything it does not define
(manufacturer, part number, temperature ratings, derating ...) is the cable's own, through ``__getattr__``.

An edit made to a conductor is made to the catalog row, so it is global: every placed cable of that part changes with it.

A shielded cable has one more conductor, its shield, that has no row (the catalog describes real conductors only):
:class:`ShieldConductor` stands in for it with fixed defaults.

The table class caches them: a wire's WHOLE set of conductors is read in one query, by :meth:`WireConductorsTable.for_wire`,
which the wires table calls from its ``__getitem__`` as the wire is loaded, so by the time anything asks the wire for its
conductors they are already here. See :mod:`harness_designer.database.create_database.wire_conductors` for the schema.
"""

from typing import TYPE_CHECKING, Union as _Union
from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import ColorMixin, MaterialMixin
from .. import id_generator as _id_generator
from ...shapes import twisted_wire as _twisted_wire
from ... import utils as _utils
from ... import check_types as _check_types


if TYPE_CHECKING:
    from ..create_database import wire_conductors as _wire_conductors
    from . import bases as _glb_bases
    from . import color as _color
    from . import material as _material
    from . import plating as _plating
    from . import wire as _wire
    from ... import splash_screen as _splash_screen


def _schema() -> "_wire_conductors":
    """The schema module, imported when it is first needed: it brings in the schema of the wires, which the database
    package cannot do while its own modules are still being imported (the schema modules of the other global tables
    are imported the same late way)."""
    from ..create_database import wire_conductors

    return wire_conductors


SHIELD_RADIUS_FRACTION = 0.4
"""A shield's own size, as a fraction of the size a conductor has inside its cable."""


class _Column:
    """A property that is one column of the row: read from the table's row cache, written through to the database (and
    announced to whatever is bound to the row)."""

    def __init__(self, nullable: bool = False):
        self._nullable = nullable
        self._name = ''

    def __set_name__(self, owner, name: str) -> None:
        self._name = name

    def __get__(self, instance, owner=None):
        if instance is None:
            return self

        return instance._table.select(self._name, id=instance._db_id)[0][0]  # NOQA

    def __set__(self, instance, value) -> None:
        instance._table.update(instance._db_id, **{self._name: value})  # NOQA
        instance._populate(self._name)  # NOQA


def _cross_section_radius(wire: "_wire.Wire", shield: bool = False) -> float:
    """The radius a conductor has in the cross-section of its cable (``shapes.twisted_wire``): half a pitch in a ribbon, else a
    circle packed with the others; the shield's is a fraction of that.

    :param wire: The cable's catalog wire.
    :param shield: Whether it is the shield's.
    """
    count = len(wire.conductors)
    size = wire.trunk_size[0] or 1.0

    if wire.is_ribbon:
        radius = wire.ribbon_pitch_mm * 0.5
    elif count >= 2:
        radius = _twisted_wire.profile(count, size)[0][2]
    elif count == 1:
        radius = size * 0.3
    else:
        radius = size * 0.25

    return radius * SHIELD_RADIUS_FRACTION if shield else radius


class _WireApi:
    """What a conductor answers the way a :class:`~.wire.Wire` does, shared by a real conductor and the shield stand-in. The
    class that mixes it in has ``wire`` (the cable's catalog wire) and the conductor's own columns."""

    def __getattr__(self, name: str):
        """Anything not defined here is the cable's (manufacturer, part number, temperature ratings, derating ...)."""
        if name.startswith('_') or name in ('wire', 'wire_id'):
            raise AttributeError(name)

        return getattr(self.wire, name)

    # ------------------------------------------------------------------ what a conductor is
    @property
    def num_conductors(self) -> int:
        """A conductor is one conductor."""
        return 1

    @property
    def shielded(self) -> bool:
        """A conductor has no shield of its own (the shield is a conductor of the cable)."""
        return False

    @property
    def tpi(self) -> float:
        """A conductor is not twisted on its own."""
        return 0.0

    @property
    def is_twisted(self) -> bool:
        """A conductor is not drawn twisted."""
        return False

    @property
    def is_cable(self) -> bool:
        """A conductor is a wire."""
        return False

    @property
    def is_ribbon(self) -> bool:
        """A conductor is a wire."""
        return False

    @property
    def cable_style(self):
        """A conductor is a wire (``CableStyle.WIRE``)."""
        from .mixins import wire_conductor as _mixin  # NOQA -- avoid a cycle at import time

        return _mixin.CableStyle.WIRE

    @property
    def conductors(self) -> tuple:
        """A conductor has no conductors inside it."""
        return ()

    @property
    def cable_part(self) -> "_wire.Wire":
        """The cable's catalog wire."""
        return self.wire

    @property
    def trunk_size(self) -> tuple[float, float]:
        """How wide and thick the conductor is drawn: round, at its own diameter."""
        return self.od_mm, self.od_mm

    # ------------------------------------------------------------------ resistance and weight
    @property
    def resistance_1kft(self) -> float:
        """The resistance of 1000 ft, ohms."""
        return self.resistance_1km * 0.3048

    @property
    def resistance_m(self) -> float:
        """The resistance of 1 m, ohms."""
        return self.resistance_1km / 1000.0

    @property
    def resistance_ft(self) -> float:
        """The resistance of 1 ft, ohms."""
        return self.resistance_1kft / 1000.0

    @property
    def _share(self) -> int:
        """How many conductors (the shield is one) the cable's weight is shared among."""
        wire = self.wire

        return max(1, len(wire.conductors) + (1 if wire.shielded else 0))

    @property
    def weight_1km(self) -> float:
        """The weight of 1 km: this conductor's share of the cable's."""
        return self.wire.weight_1km / self._share

    @property
    def weight_1kft(self) -> float:
        """The weight of 1000 ft: its share of the cable's."""
        return self.wire.weight_1kft / self._share

    @property
    def weight_g_m(self) -> float:
        """The weight of 1 m in grams: its share of the cable's."""
        return self.wire.weight_g_m / self._share

    @property
    def weight_g_ft(self) -> float:
        """The weight of 1 ft in grams: its share of the cable's."""
        return self.wire.weight_g_ft / self._share

    @property
    def weight_lb_ft(self) -> float:
        """The weight of 1 ft in pounds: its share of the cable's."""
        return self.wire.weight_lb_ft / self._share

    # ------------------------------------------------------------------ size (the same maths as Wire)
    @property
    def conductor_dia_in(self) -> float:
        """The diameter of the metal, inches."""
        return self.conductor_dia_mm / 25.4

    @property
    def size_in2(self) -> float:
        """The cross-section of the metal, square inches."""
        return _utils.mm2_to_in2(self.size_mm2, self.strands)

    @property
    def in2_symbol(self) -> str:
        """The unit symbol."""
        return 'in²'

    @property
    def mm2_symbol(self) -> str:
        """The unit symbol."""
        return 'mm²'


class WireConductor(_WireApi, EntryBase, ColorMixin, MaterialMixin):
    """One conductor inside a multi-conductor wire (a ``wire_conductors`` row). Editing it edits the catalog."""

    _table: "WireConductorsTable" = None

    wire_id = _Column()
    """The cable's row in ``wires`` (this conductor belongs to it)."""

    idx = _Column()
    """The conductor's position within the cable; the first is ``0``."""

    resistance_1km = _Column()
    """The resistance per km of the conductor, in ohms."""

    @property
    @_check_types.do
    def id(self) -> bytes:
        """The row id (as ``db_id``)."""
        return self._db_id

    @property
    @_check_types.do
    def wire(self) -> "_wire.Wire":
        """The cable's catalog wire."""
        return self._table.db.wires_table[self.wire_id]

    # ------------------------------------------------------------------ colours (``color`` is the mixin's)
    @property
    @_check_types.do
    def stripe_color_id(self) -> bytes:
        """The colour id of the stripe; ``id_generator.NO_COLOR_UUID`` when it has none."""
        return self._table.select('stripe_color_id', id=self._db_id)[0][0]

    @stripe_color_id.setter
    @_check_types.do
    def stripe_color_id(self, value: bytes) -> None:
        self._table.update(self._db_id, stripe_color_id=value)
        self._populate('stripe_color_id')

    @property
    @_check_types.do
    def has_stripe(self) -> bool:
        """Whether the conductor has a stripe."""
        return self.stripe_color_id != _id_generator.NO_COLOR_UUID.bytes

    @property
    @_check_types.do
    def stripe_color(self) -> _Union["_color.Color", None]:
        """The colour of the stripe; ``None`` for a conductor without one."""
        if not self.has_stripe:
            return None

        return self._table.db.colors_table[self.stripe_color_id]

    # ------------------------------------------------------------------ materials (``material`` is the mixin's: the insulation)
    @property
    @_check_types.do
    def core_material_id(self) -> bytes:
        """The plating (core material) id of the metal."""
        return self._table.select('core_material_id', id=self._db_id)[0][0]

    @core_material_id.setter
    @_check_types.do
    def core_material_id(self, value: bytes) -> None:
        self._table.update(self._db_id, core_material_id=value)
        self._populate('core_material_id')

    @property
    @_check_types.do
    def core_material(self) -> "_plating.Plating":
        """The plating (core material) of the metal."""
        return self._table.db.platings_table[self.core_material_id]

    # ------------------------------------------------------------------ size
    @property
    @_check_types.do
    def strands(self) -> int:
        """The number of strands."""
        return self._table.select('strands', id=self._db_id)[0][0]

    @strands.setter
    @_check_types.do
    def strands(self, value: int) -> None:
        self._table.update(self._db_id, strands=value)
        self._populate('strands')

    @property
    @_check_types.do
    def conductor_dia_mm(self) -> float:
        """The diameter of the metal, mm: the stored one, else worked out from the cross-section or AWG; 0.0 for none."""
        mm = self._table.select('wire_size_dia', id=self._db_id)[0][0]

        if mm is None:
            cross = self._table.select('wire_size_cross', id=self._db_id)[0][0]
            awg = self._table.select('wire_size_awg', id=self._db_id)[0][0]

            if cross is not None:
                mm = _utils.mm2_to_d_mm(cross, self.strands)
            elif awg is not None:
                mm = _utils.awg_to_d_mm(awg, self.strands)

        return 0.0 if mm is None else mm

    @conductor_dia_mm.setter
    @_check_types.do
    def conductor_dia_mm(self, value: float) -> None:
        # the three ways of giving a size are kept in step, as Wire does
        self._table.update(self._db_id, wire_size_dia=value, wire_size_awg=_utils.d_mm_to_awg(value, self.strands),
                           wire_size_cross=_utils.d_mm_to_mm2(value, self.strands))
        self._populate('conductor_dia_mm')

    @property
    @_check_types.do
    def size_mm2(self) -> float:
        """The cross-section of the metal, mm^2: the stored one, else worked out from the AWG or diameter; 0.0 for none."""
        mm2 = self._table.select('wire_size_cross', id=self._db_id)[0][0]

        if mm2 is None:
            awg = self._table.select('wire_size_awg', id=self._db_id)[0][0]
            dia = self._table.select('wire_size_dia', id=self._db_id)[0][0]

            if awg is not None:
                mm2 = _utils.awg_to_mm2(awg, self.strands)
            elif dia is not None:
                mm2 = _utils.d_mm_to_mm2(dia, self.strands)

        return 0.0 if mm2 is None else mm2

    @size_mm2.setter
    @_check_types.do
    def size_mm2(self, value: float) -> None:
        self._table.update(self._db_id, wire_size_cross=value, wire_size_awg=_utils.mm2_to_awg(value, self.strands),
                           wire_size_dia=_utils.mm2_to_d_mm(value, self.strands))
        self._populate('size_mm2')

    @property
    @_check_types.do
    def size_awg(self) -> _Union[int, None]:
        """The AWG size: the stored one, else worked out from the cross-section or diameter; ``None`` for none."""
        awg = self._table.select('wire_size_awg', id=self._db_id)[0][0]

        if awg is None:
            cross = self._table.select('wire_size_cross', id=self._db_id)[0][0]
            dia = self._table.select('wire_size_dia', id=self._db_id)[0][0]

            if cross is not None:
                awg = _utils.mm2_to_awg(cross, self.strands)
            elif dia is not None:
                awg = _utils.d_mm_to_awg(dia, self.strands)

        return awg

    @size_awg.setter
    @_check_types.do
    def size_awg(self, value: int) -> None:
        self._table.update(self._db_id, wire_size_awg=value, wire_size_dia=_utils.awg_to_d_mm(value, self.strands),
                           wire_size_cross=_utils.awg_to_mm2(value, self.strands))
        self._populate('size_awg')

    @property
    @_check_types.do
    def od_mm(self) -> float:
        """The diameter over the conductor's insulation, mm: the stored one, or, when the catalog gave none (0), the size it
        has in the cable's cross-section, so that it is drawn as thick as it is inside the cable."""
        od = self._table.select('od_mm', id=self._db_id)[0][0]

        return od if od else 2.0 * _cross_section_radius(self.wire)

    @od_mm.setter
    @_check_types.do
    def od_mm(self, value: float) -> None:
        self._table.update(self._db_id, od_mm=value)
        self._populate('od_mm')

    @property
    @_check_types.do
    def stored_od_mm(self) -> float:
        """The diameter over the insulation as the catalog stores it (0 when it gave none), which ``od_mm`` replaces with the
        size the conductor has in its cable. The cable's own size code reads this one (``od_mm`` would ask the cable)."""
        return self._table.select('od_mm', id=self._db_id)[0][0]


class ShieldConductor(_WireApi):
    """The shield of a shielded cable, which has no ``wire_conductors`` row (the catalog describes real conductors only): it
    stands in as the ``part`` of the shield's placed row with fixed values. Read-only. It has no colour of its own ("no
    color": drawn as bare metal), is a fraction of a conductor's size, and has no resistance of its own."""

    def __init__(self, wire: "_wire.Wire"):
        """Initialise the :class:`ShieldConductor` instance.

        :param wire: The cable's catalog wire.
        """
        self._wire = wire

    @property
    def wire(self) -> "_wire.Wire":
        """The cable's catalog wire."""
        return self._wire

    @property
    def id(self) -> None:
        """A shield has no row."""
        return None

    @property
    def db_id(self) -> None:
        """A shield has no row."""
        return None

    @property
    def wire_id(self) -> bytes:
        """The cable's row in ``wires``."""
        return self._wire.db_id

    @property
    def idx(self) -> int:
        """The shield is the last of the cable's conductors."""
        return len(self._wire.conductors)

    @property
    def _db(self):
        return self._wire._table.db  # NOQA

    @property
    def color_id(self) -> bytes:
        """"No color"."""
        return _id_generator.NO_COLOR_UUID.bytes

    @property
    def color(self) -> "_color.Color":
        """The shield has no colour: "no color"."""
        return self._db.colors_table[self.color_id]

    @property
    def stripe_color_id(self) -> bytes:
        """"No color": no stripe."""
        return _id_generator.NO_COLOR_UUID.bytes

    @property
    def has_stripe(self) -> bool:
        """A shield has no stripe."""
        return False

    @property
    def stripe_color(self) -> None:
        """A shield has no stripe."""
        return None

    @property
    def material_id(self) -> bytes:
        """The cable's own."""
        return self._wire.material_id

    @property
    def material(self) -> "_material.Material":
        """The cable's own."""
        return self._wire.material

    @property
    def core_material_id(self) -> bytes:
        """The cable's own."""
        return self._wire.core_material_id

    @property
    def core_material(self) -> "_plating.Plating":
        """The cable's own."""
        return self._wire.core_material

    @property
    def strands(self) -> int:
        """One."""
        return 1

    @property
    def conductor_dia_mm(self) -> float:
        """No size of its own."""
        return 0.0

    @property
    def size_mm2(self) -> float:
        """No size of its own."""
        return 0.0

    @property
    def size_awg(self) -> None:
        """No size of its own."""
        return None

    @property
    def od_mm(self) -> float:
        """A fraction of the size a conductor has in the cable."""
        return 2.0 * _cross_section_radius(self._wire, shield=True)

    @property
    def resistance_1km(self) -> float:
        """No resistance of its own."""
        return 0.0


class WireConductorsTable(TableBase):
    """Manage the ``wire_conductors`` table, and hold the conductors of every wire that has been loaded."""

    __table_name__ = 'wire_conductors'

    @_check_types.do
    def __init__(self, db: "_glb_bases.GLBTables", table_names: list[str], splash: "_splash_screen.Splash",
                 load_database: bool):
        """Create the table if it is missing and make sure a wire's rows can be found without reading every row.

        :param db: Database accessor.
        :type db: :class:`GLBTables`
        :param table_names: The tables the database already has.
        :type table_names: list[str]
        :param splash: The splash screen.
        :type splash: :class:`_splash_screen.Splash`
        :param load_database: Whether to load the database.
        :type load_database: bool
        """
        # wire id -> that wire's conductors (empty when it has none), filled by for_wire
        self._by_wire: dict[bytes, tuple[WireConductor, ...]] = {}

        TableBase.__init__(self, db, table_names, splash, load_database)

        # the catalog may have been built by something that knows nothing of this index, so ask every start
        _schema().add_indexes(self)

    @_check_types.do
    def _table_needs_update(self) -> bool:
        return _schema().table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self, _: "_splash_screen.Splash") -> None:
        _schema().table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        _schema().table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable[WireConductor]:
        for db_id in TableBase.__iter__(self):
            yield WireConductor(self, db_id)

    @_check_types.do
    def __getitem__(self, item: bytes) -> WireConductor:
        if item in WireConductor or item in self:
            return WireConductor(self, item)

        raise KeyError(item)

    @_check_types.do
    def for_wire(self, wire_id: bytes) -> tuple[WireConductor, ...]:
        """Return a wire's conductors, first conductor first.

        Read from the database in one query the first time a wire is asked about (a wire with no conductors rows
        is remembered as having none, so it is not asked about again), then served from memory.

        :param wire_id: The wire's row id.
        :type wire_id: bytes
        :returns: The wire's conductors by ``idx``; empty for a single-conductor wire.
        :rtype: tuple[WireConductor, ...]
        """
        rows = self._by_wire.get(wire_id)

        if rows is None:
            self._con.execute(f'SELECT id FROM {self.__table_name__} WHERE wire_id = ? ORDER BY idx;', (wire_id,))

            rows = tuple(WireConductor(self, row[0]) for row in self._con.fetchall())
            self._by_wire[wire_id] = rows

        return rows

    @_check_types.do
    def forget(self, wire_id: bytes) -> None:
        """Drop a wire's conductors from memory, so the next :meth:`for_wire` reads them again.

        :param wire_id: The wire's row id.
        :type wire_id: bytes
        """
        self._by_wire.pop(wire_id, None)

    @_check_types.do
    def insert(self, wire_id: bytes, idx: int, color_id: bytes, stripe_color_id: bytes, core_material_id: bytes,
               material_id: bytes, wire_size_dia: float | None = None, wire_size_cross: float | None = None,
               wire_size_awg: int | None = None, strands: int = 1, od_mm: float = 0.0,
               resistance_1km: float = 0.0) -> WireConductor:
        """Add one conductor to a wire. The wire's conductors in memory, if it has any, are dropped and read again
        the next time they are asked for.

        :param wire_id: The cable the conductor sits in.
        :type wire_id: bytes
        :param idx: The conductor's position within the cable.
        :type idx: int
        :param color_id: The colour of the conductor's insulation.
        :type color_id: bytes
        :param stripe_color_id: The colour of its stripe; ``id_generator.NO_COLOR_UUID`` for none.
        :type stripe_color_id: bytes
        :param core_material_id: The plating of the metal.
        :type core_material_id: bytes
        :param material_id: The insulation.
        :type material_id: bytes
        :param wire_size_dia: The diameter of the stranded metal, in mm.
        :type wire_size_dia: float | None
        :param wire_size_cross: The cross-section of the metal, in mm^2.
        :type wire_size_cross: float | None
        :param wire_size_awg: The AWG size.
        :type wire_size_awg: int | None
        :param strands: The number of strands.
        :type strands: int
        :param od_mm: The diameter over the conductor's insulation, in mm.
        :type od_mm: float
        :param resistance_1km: The resistance per km of cable, in ohms.
        :type resistance_1km: float
        :returns: The new row.
        :rtype: WireConductor
        """
        db_id = TableBase.insert(
            self, wire_id=wire_id, idx=idx, color_id=color_id, stripe_color_id=stripe_color_id,
            core_material_id=core_material_id, material_id=material_id, wire_size_dia=wire_size_dia,
            wire_size_cross=wire_size_cross, wire_size_awg=wire_size_awg, strands=strands, od_mm=od_mm,
            resistance_1km=resistance_1km)

        self.forget(wire_id)

        return self[db_id]
