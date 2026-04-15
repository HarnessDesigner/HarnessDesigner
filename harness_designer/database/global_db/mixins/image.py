from .base import BaseMixin


class ImageMixin(BaseMixin):

    @property
    def image(self) -> "_image.Image":
        image_id = self._table.select('image_id', id=self._db_id)
        return _image.Image(self._table.db.images_table, image_id[0][0])

    @image.setter
    def image(self, value: "_image.Image"):
        self._table.update(self._db_id, image_id=value.db_id)

    @property
    def image_id(self) -> int:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @image_id.setter
    def image_id(self, value: int):
        self._table.update(self._db_id, image_id=value)


from .. import image as _image  # NOQA
