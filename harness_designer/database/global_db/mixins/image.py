# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


class ImageMixin(BaseMixin):
    """Represent an image mixin in :mod:`harness_designer.database.global_db.mixins.image`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_image: "DefaultStoredValueType | _image.Image" = DefaultStoredValue

    @property
    def image(self) -> "_image.Image":
        """Return the image.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_image.Image`
        """
        if self._stored_image is DefaultStoredValue:
            image_id = self._table.select('image_id', id=self._db_id)
            self._stored_image = _image.Image(self._table.db.images_table, image_id[0][0])

        return self._stored_image

    _stored_image_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def image_id(self) -> int:
        """Return the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_image_id is DefaultStoredValue:
            self._stored_image_id = self._table.select('image_id', id=self._db_id)[0][0]

        return self._stored_image_id

    @image_id.setter
    def image_id(self, value: int):
        """Set the image ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_image_id = value
        self._stored_image = DefaultStoredValue

        self._table.update(self._db_id, image_id=value)
        self._populate('image_id')


from .. import image as _image  # NOQA
