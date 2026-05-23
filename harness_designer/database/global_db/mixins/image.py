# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin


class ImageMixin(BaseMixin):
    """Represent an image mixin in :mod:`harness_designer.database.global_db.mixins.image`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def image(self) -> "_image.Image":
        """Return the image.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_image.Image`
        """
        image_id = self._table.select('image_id', id=self._db_id)
        return _image.Image(self._table.db.images_table, image_id[0][0])

    @property
    def image_id(self) -> int:
        """Return the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('image_id', id=self._db_id)[0][0]

    @image_id.setter
    def image_id(self, value: int):
        """Set the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, image_id=value)
        self._populate('image_id')


from .. import image as _image  # NOQA
